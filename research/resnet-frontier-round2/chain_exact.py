"""Exact minimum additional work at a fixed cap on chain-ordered DAGs.

This research module does not change the normative verifier. Every adjacent pair
must have a direct dependency, forcing first-forward and backward orders. Retained
sets and regeneration remain unrestricted. Limit exhaustion never returns a bound.
"""
import argparse
import heapq
import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from verifier import load, validate_graph, verify
from search import certificate


class Limited(RuntimeError):
    pass


def solve(graph, cap, budget, max_states=700000, seconds=120, astar=True, use_lower_bound=True):
    validate_graph(graph)
    if any(type(x) is not int or x < 0 for x in (cap, budget, max_states)):
        raise ValueError('cap, budget, max_states must be nonnegative integers')
    if max_states < 1 or type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds <= 0:
        raise ValueError('positive finite time and state bounds required')
    nodes = graph['nodes']
    n = len(nodes)
    if n > 24:
        raise ValueError('research chain domain limited to24 nodes')
    index = {v['id']: i for i, v in enumerate(nodes)}
    if any(nodes[i-1]['id'] not in nodes[i]['deps'] for i in range(1, n)):
        raise ValueError('direct adjacent dependency required: orders must be forced')
    mask = lambda names: sum(1 << index[x] for x in names if x in index)
    deps = [mask(v['deps']) for v in nodes]
    reqs = [mask(v['backward_requires']) for v in nodes]
    costs = [v['cost'] for v in nodes]
    sizes = [v['bytes'] for v in nodes]
    fixed = sum(v['bytes'] for v in graph['inputs'])
    full = (1 << n)-1
    outputs = mask(graph['outputs'])
    forbidden = mask(v['id'] for v in nodes if not v['recomputable'])
    # req_prefix[b] is every saved internal value demanded by backward0..b-1.
    req_prefix = [0]
    ancestors = []
    for i in range(n):
        req_prefix.append(req_prefix[-1] | reqs[i])
        closure = (1 << i) | deps[i]
        todo = deps[i]
        while todo:
            bit = todo & -todo
            todo ^= bit
            closure |= ancestors[bit.bit_length()-1]
        ancestors.append(closure)
    future_deps = [0] * (n+1)
    for i in range(n-1, -1, -1):
        future_deps[i] = future_deps[i+1] | deps[i]
    useful = [0]
    for b in range(1, n+1):
        required = req_prefix[b]
        closure = required
        while required:
            bit = required & -required
            required ^= bit
            closure |= ancestors[bit.bit_length()-1]
        useful.append(closure)
    uniform = len(set(sizes)) == 1
    def memory(live):
        if uniform:
            return fixed + live.bit_count()*sizes[0]
        result = fixed
        while live:
            bit = live & -live
            result += sizes[bit.bit_length()-1]
            live ^= bit
        return result
    # b=-1 before loss, otherwise backward nodes0..b-1 remain.
    def normalize(live, seen, b):
        tail = []
        if b == -1 and seen == n and live & outputs == outputs:
            b = n
            tail.append(dict(op='loss'))
        if b >= 0:
            while b and live & reqs[b-1] == reqs[b-1]:
                b -= 1
                tail.append(dict(op='backward', node=nodes[b]['id']))
            dead = live & ~useful[b]
            while dead:
                bit = dead & -dead
                dead ^= bit
                live ^= bit
                tail.append(dict(op='drop', node=nodes[bit.bit_length()-1]['id']))
        return (live, seen, b), tuple(tail)
    def lower_bound(state):
        live, seen, b = state
        targets = req_prefix[n] | future_deps[seen] | outputs if b == -1 else req_prefix[b]
        needed = targets & ~live
        # Recursively close demands through absent dependencies, stopping at live
        # tensors. Each missing seen operation must execute at least once.
        closure = 0
        while needed:
            bit = needed & -needed
            needed ^= bit
            if closure & bit:
                continue
            closure |= bit
            needed |= deps[bit.bit_length()-1] & ~live & ~closure
        charged = closure & ((1 << seen)-1)
        if charged & forbidden:
            return budget+1
        result = 0
        while charged:
            bit = charged & -charged
            charged ^= bit
            result += costs[bit.bit_length()-1]
        return result
    start = (0, 0, -1)
    # Immutable records preserve parent chains after a state receives a cheaper label.
    records = [(start, 0, None, ())]
    best = {start: (0, 0)}
    queue = [(0, 0, 0)]
    expanded = pruned = 0
    started = time.monotonic()
    if fixed > cap:
        return dict(status='INFEASIBLE', states=1, expanded=0, seconds=0), None
    while queue:
        _, spent, rid = heapq.heappop(queue)
        state, _, parent, actions = records[rid]
        if best.get(state) != (spent, rid):
            continue
        if time.monotonic()-started > seconds:
            raise Limited(f'time limit{seconds}s; no optimum/infeasibility claim')
        live, seen, b = state
        expanded += 1
        if b == 0:
            path = []
            while records[rid][2] is not None:
                path.extend(reversed(records[rid][3]))
                rid = records[rid][2]
            path.reverse()
            stats = dict(status='OPTIMAL', minimum_recompute_cost=spent,
                         states=len(records), logical_states=len(best), expanded=expanded,
                         pruned=pruned, seconds=time.monotonic()-started, cap=cap,
                         budget=budget, astar=astar, lower_bound_pruning=use_lower_bound, global_for_chain_domain=True)
            c = certificate(graph, path, budget, 'chain-fixed-cap-exact', stats)
            assert c['claims']['recompute_cost'] == spent
            assert c['claims']['peak_bytes'] <= cap
            verify(graph, c, budget)
            return stats, c
        moves = []
        # All legal drops. Canonicalization only drops values with no remaining
        # forward or saved-value use after the loss barrier.
        todo = live
        while todo:
            bit = todo & -todo
            todo ^= bit
            moves.append((live^bit, seen, b, 0, dict(op='drop', node=nodes[bit.bit_length()-1]['id'])))
        for i in range(seen + int(seen < n and b == -1)):
            bit = 1 << i
            if live & bit or live & deps[i] != deps[i]:
                continue
            repeated = i < seen
            if repeated and not nodes[i]['recomputable']:
                continue
            extra = costs[i] if repeated else 0
            if spent+extra > budget or memory(live)+sizes[i] > cap:
                continue
            moves.append((live|bit, max(seen, i+1), b, extra, dict(op='forward', node=nodes[i]['id'])))
        for next_live, next_seen, next_b, extra, action in moves:
            target, tail = normalize(next_live, next_seen, next_b)
            new_cost = spent+extra
            if new_cost >= best.get(target, (10**100,))[0]:
                pruned += 1
                continue
            heuristic = lower_bound(target) if use_lower_bound else 0
            if new_cost+heuristic > budget:
                pruned += 1
                continue
            if len(records) >= max_states:
                raise Limited(f'state limit{max_states}; no optimum/infeasibility claim')
            nr = len(records)
            records.append((target, new_cost, rid, (action,)+tail))
            best[target] = (new_cost, nr)
            heapq.heappush(queue, (new_cost+(heuristic if astar else 0), new_cost, nr))
    return dict(status='INFEASIBLE', states=len(records), logical_states=len(best),
                expanded=expanded, pruned=pruned, seconds=time.monotonic()-started,
                cap=cap, budget=budget, astar=astar, lower_bound_pruning=use_lower_bound, global_for_chain_domain=True), None


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--graph', required=True)
    p.add_argument('--cap', type=int, required=True)
    p.add_argument('--budget', type=int, required=True)
    p.add_argument('--states', type=int, default=700000)
    p.add_argument('--seconds', type=float, default=120)
    p.add_argument('--out', required=True)
    p.add_argument('--dijkstra', action='store_true')
    p.add_argument('--no-lower-bound', action='store_true')
    args = p.parse_args()
    started = time.monotonic()
    try:
        stats, c = solve(load(args.graph), args.cap, args.budget, args.states, args.seconds, not args.dijkstra, not args.no_lower_bound)
    except Limited as error:
        stats, c = dict(status='LIMITED', reason=str(error), seconds=time.monotonic()-started), None
    Path(args.out+'.stats.json').write_text(json.dumps(stats, indent=2)+'\n')
    if c:
        Path(args.out).write_text(json.dumps(c, indent=2)+'\n')
    print(json.dumps(stats, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
