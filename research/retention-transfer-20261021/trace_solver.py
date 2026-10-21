"""Finite optional-forward-slot synthesis; no global optimality claim.

Backward/loss order is fixed. Every supplied forward occurrence is optional.
The solver jointly chooses executions and retained tensors, with output allocation
charged before input drops. Extraction uses the independent project verifier.
"""
import argparse
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from ortools.sat.python import cp_model
import ortools
from verifier import load, validate_graph, verify
from search import certificate


def validate_slots(g, slots):
    nodes = {v['id']: v for v in g['nodes']}
    done = set()
    phase = False
    for a in slots:
        op, name = a['op'], a.get('node')
        if op == 'loss':
            if phase:
                raise ValueError('repeated loss slot')
            phase = True
        elif op in ('forward', 'backward') and name in nodes:
            if op == 'backward':
                children = {v['id'] for v in nodes.values() if name in v['deps']}
                if not phase or name in done or not children <= done:
                    raise ValueError('invalid fixed backward order')
                done.add(name)
        else:
            raise ValueError('unknown slot')
    if not phase or done != set(nodes):
        raise ValueError('incomplete fixed backward/loss slots')


def solve_slots(g, slots, budget, cap, seconds=30, hint=None, workers=1,
                seed=20261021, log=False, strategy='default'):
    validate_graph(g)
    validate_slots(g, slots)
    if any(type(v) is not int or v < 0 for v in (budget, cap)):
        raise ValueError('budget and cap must be nonnegative integers')
    ns, total = g['nodes'], len(slots)
    n = len(ns)
    if n * (total + 1) > 200000:
        raise ValueError('finite slot variable cap exceeded; no infeasibility claim')
    idx = {v['id']: i for i, v in enumerate(ns)}
    fixed = sum(v['bytes'] for v in g['inputs'])
    unit = math.gcd(fixed, *(v['bytes'] for v in ns))
    cost_unit = math.gcd(*(v['cost'] for v in ns))
    baseline = sum(v['cost'] for v in ns)
    m = cp_model.CpModel()
    live = [[m.new_bool_var(f'l_{t}_{i}') for i in range(n)]
            for t in range(total + 1)]
    run = {t: m.new_bool_var(f'f_{t}') for t, a in enumerate(slots)
           if a['op'] == 'forward'}
    for i in range(n):
        m.add(live[0][i] == 0)
    loss_at = next(t for t, a in enumerate(slots) if a['op'] == 'loss')
    for i, v in enumerate(ns):
        before = [run[t] for t in run if t < loss_at and slots[t]['node'] == v['id']]
        occurrences = [run[t] for t in run if slots[t]['node'] == v['id']]
        m.add(sum(before) >= 1)
        if not v['recomputable']:
            m.add(sum(occurrences) == 1)
    for t in range(total + 1):
        mem = fixed // unit + sum((v['bytes'] // unit) * live[t][i]
                                  for i, v in enumerate(ns))
        m.add(mem <= cap // unit)
        if t == total:
            continue
        a = slots[t]
        op, name = a['op'], a.get('node')
        produced = idx[name] if op == 'forward' else None
        if op == 'forward':
            v = ns[produced]
            m.add(live[t][produced] + run[t] <= 1)
            for dep in v['deps']:
                if dep in idx:
                    m.add(run[t] <= live[t][idx[dep]])
            m.add(mem + (v['bytes'] // unit) * run[t] <= cap // unit)
        else:
            required = g['outputs'] if op == 'loss' else ns[idx[name]]['backward_requires']
            for dep in required:
                if dep in idx:
                    m.add(live[t][idx[dep]] == 1)
        for i in range(n):
            m.add(live[t + 1][i] <= live[t][i] + (run[t] if i == produced else 0))
    work = sum((ns[idx[slots[t]['node']]]['cost'] // cost_unit) * var
               for t, var in run.items())
    m.add(work <= (baseline + budget) // cost_unit)
    m.minimize(work)
    if strategy == 'cost-first':
        ordered = sorted(run, key=lambda t: (-ns[idx[slots[t]['node']]]['cost'], t))
        m.add_decision_strategy([run[t] for t in ordered], cp_model.CHOOSE_FIRST,
                                cp_model.SELECT_MIN_VALUE)
    elif strategy != 'default':
        raise ValueError('unknown search strategy')
    if hint is not None:
        for t, row in enumerate(hint['live']):
            for i in range(n):
                m.add_hint(live[t][i], int(bool(row & (1 << i))))
        for t, var in run.items():
            m.add_hint(var, int(t in hint['run']))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = seconds
    solver.parameters.num_search_workers = workers
    solver.parameters.random_seed = seed
    solver.parameters.log_search_progress = log
    if strategy == 'cost-first':
        solver.parameters.search_branching = cp_model.FIXED_SEARCH
    started = time.perf_counter()
    status = solver.solve(m)
    stats = dict(status=solver.status_name(status), seconds=time.perf_counter() - started,
                 slots=total, forward_slots=len(run), cap=cap, budget=budget,
                 workers=workers, seed=seed, solver='OR-Tools ' + ortools.__version__,
                 strategy=strategy,
                 global_optimal=False, scope='supplied finite forward slots; fixed backward order',
                 best_bound_forward_cost=solver.best_objective_bound * cost_unit)
    if status not in (cp_model.FEASIBLE, cp_model.OPTIMAL):
        return stats, None
    actions, actual = [], set()
    for t, a in enumerate(slots):
        target = {v['id'] for i, v in enumerate(ns) if solver.value(live[t][i])}
        if not target <= actual:
            raise AssertionError('solver invented a live tensor')
        for name in sorted(actual - target):
            actions.append(dict(op='drop', node=name))
        actual = target
        if a['op'] != 'forward' or solver.value(run[t]):
            actions.append(dict(a))
            if a['op'] == 'forward':
                actual.add(a['node'])
    c = certificate(g, actions, budget, 'optional-slot-rematerialization', stats)
    verify(g, c, budget)
    if c['claims']['peak_bytes'] > cap:
        raise AssertionError('extracted schedule exceeded cap')
    stats.update(c['claims'])
    return stats, c


def incumbent_slots(g, actions, expansion='none'):
    """Insert one topological ancestor sweep before selected demands.

    These are finite construction opportunities, not unconstrained action steps.
    The incumbent's own non-drop actions and its exact live-state hint survive.
    """
    ns = g['nodes']
    idx = {v['id']: i for i, v in enumerate(ns)}
    ancestors = {}
    for v in ns:
        closure = {v['id']}
        for d in v['deps']:
            closure |= ancestors.get(d, set())
        ancestors[v['id']] = closure
    slots, lives, runs, actual = [], [], set(), 0
    for a in actions:
        op, name = a['op'], a.get('node')
        if op == 'drop':
            actual &= ~(1 << idx[name])
            continue
        targets = set()
        if expansion in ('backward', 'all') and op == 'backward':
            for req in ns[idx[name]]['backward_requires']:
                targets |= ancestors.get(req, set())
        if expansion == 'all' and op == 'forward':
            for req in ns[idx[name]]['deps']:
                targets |= ancestors.get(req, set())
        if expansion == 'local' and op in ('forward', 'backward'):
            reads = ns[idx[name]]['deps' if op == 'forward' else 'backward_requires']
            for req in reads:
                if req in idx:
                    targets.add(req)
        for v in ns:
            if v['id'] in targets:
                slots.append(dict(op='forward', node=v['id']))
                lives.append(actual)
        lives.append(actual)
        if op == 'forward':
            runs.add(len(slots))
            actual |= 1 << idx[name]
        slots.append(dict(a))
    lives.append(actual)
    return slots, dict(live=lives, run=runs)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--graph', required=True)
    p.add_argument('--incumbent', required=True)
    p.add_argument('--budget', type=int, required=True)
    p.add_argument('--cap', type=int, required=True)
    p.add_argument('--seconds', type=float, default=60)
    p.add_argument('--expand', choices=['none', 'local', 'backward', 'all'], default='none')
    p.add_argument('--out', required=True)
    p.add_argument('--log', action='store_true')
    p.add_argument('--workers', type=int, default=1)
    p.add_argument('--strategy', choices=['default', 'cost-first'], default='default')
    a = p.parse_args()
    g, source = load(a.graph), load(a.incumbent)
    verify(g, source, source['budget'])
    slots, hint = incumbent_slots(g, source['actions'], a.expand)
    stats, c = solve_slots(g, slots, a.budget, a.cap, a.seconds, hint=hint, log=a.log,
                           workers=a.workers, strategy=a.strategy)
    stats['expansion'] = a.expand
    if c:
        c['metadata']['expansion'] = a.expand
        Path(a.out).write_text(json.dumps(c, indent=2) + '\n')
    print(json.dumps(stats, sort_keys=True), flush=True)
    return 0 if c else 2


if __name__ == '__main__':
    raise SystemExit(main())
