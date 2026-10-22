"""Allocation-induced last-barrier cuts for activation-memory/v1.

If a forward transition exactly fills a proposed cap, its live set is forced.
Before a mandatory target's first execution, take the last such ancestor event.
Relax all later memory/work constraints but forbid another event in that set.
If the target cannot be derived from ANY forced live set, the cap is impossible.
This is a forward-only necessary condition, valid at every recomputation budget.
"""
import argparse
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from verifier import MODEL, digest, integer, load, require, validate_graph


def graph_facts(g):
    validate_graph(g)
    nodes = {n['id']: n for n in g['nodes']}
    inputs = {n['id'] for n in g['inputs']}
    sizes = {n['id']: n['bytes'] for n in g['inputs'] + g['nodes']}
    ancestors = {n: set() for n in inputs}
    allocations = {}
    for name, node in nodes.items():
        ancestors[name] = set(node['deps'])
        for dep in node['deps']:
            ancestors[name] |= ancestors[dep]
        allocations[name] = inputs | set(node['deps']) | {name}
    return nodes, inputs, sizes, ancestors, allocations


def reachable(g, initial, forbidden):
    # A topological pass is the least fixed point. Unbounded live memory and free
    # execution of every other node deliberately enlarge the feasible set.
    available = set(initial)
    for node in g['nodes']:
        if node['id'] not in forbidden and set(node['deps']) <= available:
            available.add(node['id'])
    return available


def make_proof(g, cap, target, barriers, facts):
    nodes, inputs, sizes, ancestors, allocations = facts
    rows = []
    for barrier in barriers:
        initial = allocations[barrier]
        closure = reachable(g, initial, set(barriers))
        if target in closure:
            return None
        rows.append(dict(barrier=barrier, live_after=sorted(initial),
                         reachable_without_barriers=sorted(closure)))
    quantum = math.gcd(*sizes.values())
    return dict(schema='last-barrier-cut/v1', model=MODEL, graph_id=g['id'],
                graph_sha256=digest(g), cap_rejected_bytes=cap,
                lower_bound_bytes=(cap // quantum + 1) * quantum,
                allocation_quantum_bytes=quantum, target=target,
                barriers=barriers, resets=rows,
                scope='Forward-allocation lower bound at every recomputation budget; '
                      'author-checked mathematical argument, not a schedule witness')


def find_cut(g):
    facts = graph_facts(g)
    nodes, inputs, sizes, ancestors, allocations = facts
    local = {name: sum(sizes[v] for v in values) for name, values in allocations.items()}
    cap = max(local.values())
    for target in nodes:
        barriers = [name for name in nodes if name in ancestors[target] and local[name] == cap]
        if barriers:
            proof = make_proof(g, cap, target, barriers, facts)
            if proof is not None:
                check_cut(g, proof)
                return proof
    return None


def check_cut(g, proof):
    facts = graph_facts(g)
    nodes, inputs, sizes, ancestors, allocations = facts
    require(isinstance(proof, dict), 'cut must be an object')
    require(proof.get('schema') == 'last-barrier-cut/v1' and proof.get('model') == MODEL,
            'wrong cut schema/model')
    require(proof.get('graph_id') == g['id'] and proof.get('graph_sha256') == digest(g),
            'cut graph identity mismatch')
    cap = proof.get('cap_rejected_bytes')
    require(integer(cap, 1), 'cut cap must be a positive integer')
    target, barriers = proof.get('target'), proof.get('barriers')
    require(isinstance(target, str) and target in nodes, 'unknown mandatory target')
    require(isinstance(barriers, list) and barriers and
            all(isinstance(b, str) and b in ancestors[target] and b in nodes for b in barriers),
            'barriers must be strict internal ancestors of the mandatory target')
    require(len(set(barriers)) == len(barriers), 'duplicate barrier')
    for barrier in barriers:
        require(sum(sizes[v] for v in allocations[barrier]) == cap,
                'barrier does not force the complete live set at this cap')
    expected = make_proof(g, cap, target, barriers, facts)
    require(expected is not None, 'target is reachable after a proposed last barrier')
    for key in ('lower_bound_bytes', 'allocation_quantum_bytes'):
        require(integer(proof.get(key), 1) and proof[key] == expected[key],
                'incorrect cut bound/granularity')
    require(proof.get('resets') == expected['resets'], 'reset closure evidence mismatch')
    return expected['lower_bound_bytes']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('graph')
    p.add_argument('--out')
    p.add_argument('--check')
    a = p.parse_args()
    g = load(a.graph)
    if a.check:
        bound = check_cut(g, load(a.check))
        print(json.dumps(dict(status='PASS', lower_bound_bytes=bound)))
    else:
        proof = find_cut(g)
        if a.out and proof is not None:
            Path(a.out).write_text(json.dumps(proof, indent=2) + '\n')
        print(json.dumps(proof, indent=2))


if __name__ == '__main__':
    main()
