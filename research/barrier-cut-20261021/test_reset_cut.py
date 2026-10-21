"""Last-barrier cut controls: exact positive case, false proofs, no-cut control."""
import copy
import heapq
import random
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from verifier import MODEL, Invalid, load
from search import exact
from reset_cut import find_cut, check_cut


def residual(join=True):
    rows = [('a', ['x'], 4), ('b', ['a'], 4), ('c', ['b'], 1),
            ('d', ['c'], 4), ('e', ['d'], 4),
            ('out', ['c', 'e'] if join else ['e'], 1)]
    return dict(model=MODEL, id='reset-residual-control', inputs=[dict(id='x', bytes=1)],
                nodes=[dict(id=n, deps=deps, bytes=size, cost=1, backward_cost=1,
                            backward_requires=[], recomputable=True)
                       for n, deps, size in rows], outputs=['out'])


def forward_optimum(g):
    """Separate exhaustive forward pebbling, with unbounded repeat work.

    This intentionally omits backward and any cost budget: a cut from forward
    allocation must also be a lower bound on this weaker problem.
    """
    nodes = g['nodes']
    ids = [n['id'] for n in nodes]
    fixed = sum(n['bytes'] for n in g['inputs'])
    deps = [sum(1 << ids.index(d) for d in n['deps'] if d in ids) for n in nodes]
    output = sum(1 << ids.index(d) for d in g['outputs'])
    full = (1 << len(nodes)) - 1
    start = (0, 0)
    best = {start: fixed}
    queue = [(fixed, start)]
    while queue:
        score, (live, seen) = heapq.heappop(queue)
        if best[live, seen] != score:
            continue
        if seen == full and live & output == output:
            return score
        for i, n in enumerate(nodes):
            bit = 1 << i
            if live & bit:
                target = (live ^ bit, seen)
            elif deps[i] & live == deps[i] and (not seen & bit or n['recomputable']):
                target = (live | bit, seen | bit)
            else:
                continue
            memory = fixed + sum(v['bytes'] for j, v in enumerate(nodes) if target[0] & (1 << j))
            candidate = max(score, memory)
            if candidate < best.get(target, float('inf')):
                best[target] = candidate
                heapq.heappush(queue, (candidate, target))
    raise AssertionError('finite graph has no eager forward schedule')


def differential_cases():
    rng = random.Random(20261021)
    cases = [residual(), residual(False)]
    # Scale and vary the two barriers, with multiple immutable inputs.
    for q in (1, 2, 3, 7):
        for large in (2, 3, 4):
            g = residual()
            for n in g['inputs'] + g['nodes']:
                n['bytes'] *= q
            for n in g['nodes']:
                if n['id'] in ('a', 'b', 'd', 'e'):
                    n['bytes'] = large * q
            cases.append(g)
            g = copy.deepcopy(g)
            g['inputs'].append(dict(id='constant', bytes=2*q))
            cases.append(g)
    for k in range(120):
        n = rng.randrange(3, 8)
        nodes = []
        for i in range(n):
            possible = ['x'] + [v['id'] for v in nodes]
            deps = rng.sample(possible, rng.randrange(1, min(len(possible), 3) + 1))
            nodes.append(dict(id=f'v{i}', deps=deps, bytes=rng.choice((1, 1, 2, 4, 4)),
                              cost=rng.randrange(1, 5), backward_cost=1,
                              recomputable=rng.random() > .15, backward_requires=[]))
        used = {v for node in nodes for v in node['deps']}
        cases.append(dict(model=MODEL, id=f'forward-differential-{k}',
                          inputs=[dict(id='x', bytes=rng.randrange(1, 4))],
                          nodes=nodes, outputs=[v['id'] for v in nodes if v['id'] not in used]))
    return cases


class ResetCutTests(unittest.TestCase):
    def test_residual_reset_cut_matches_exact_optimum(self):
        g = residual()
        proof = find_cut(g)
        self.assertIsNotNone(proof)
        self.assertEqual(check_cut(g, proof), 10)
        self.assertEqual(exact(g, 12)['claims']['peak_bytes'], 10)

    def test_chain_without_join_has_no_cut(self):
        self.assertIsNone(find_cut(residual(join=False)))
        self.assertEqual(exact(residual(join=False), 12)['claims']['peak_bytes'], 9)

    def test_false_bound_and_incomplete_barrier_list_rejected(self):
        g = residual()
        proof = find_cut(g)
        bad = copy.deepcopy(proof)
        bad['lower_bound_bytes'] += 1
        with self.assertRaises(Invalid):
            check_cut(g, bad)
        bad = copy.deepcopy(proof)
        bad['barriers'] = bad['barriers'][:1]
        with self.assertRaises(Invalid):
            check_cut(g, bad)

    def test_fixed_transformer_bound_is_ten_units(self):
        g = load(ROOT / 'benchmarks/graphs/transformer-b4-t128.json')
        proof = find_cut(g)
        self.assertEqual(check_cut(g, proof), 1310720)
        self.assertEqual(proof['target'], 'b0_residual2')

    def test_cuts_never_exceed_separate_exhaustive_forward_optimum(self):
        cut_count = 0
        for g in differential_cases():
            proof = find_cut(g)
            optimum = forward_optimum(g)
            if proof is not None:
                cut_count += 1
                self.assertLessEqual(check_cut(g, proof), optimum, g['id'])
        self.assertGreaterEqual(cut_count, 20)

    def test_all_fixed_tiny_cases_stay_below_full_reference_optima(self):
        rows = [r for r in load(ROOT / 'records/working-frontiers.json')
                if r['bound_method'] == 'exact-minimax']
        self.assertEqual(len(rows), 25)
        for row in rows:
            g = load(ROOT / f"benchmarks/graphs/{row['graph']}.json")
            proof = find_cut(g)
            if proof is not None:
                self.assertLessEqual(check_cut(g, proof), row['peak_bytes'])

    def test_unknown_or_nonancestor_barriers_and_stale_hash_rejected(self):
        g = residual()
        proof = find_cut(g)
        for barrier in ('unknown', 'out', 'x'):
            bad = copy.deepcopy(proof)
            bad['barriers'] = [barrier]
            with self.assertRaises(Invalid):
                check_cut(g, bad)
        bad = copy.deepcopy(proof)
        bad['graph_sha256'] = '0' * 64
        with self.assertRaises(Invalid):
            check_cut(g, bad)
        bad = copy.deepcopy(proof)
        bad['cap_rejected_bytes'] = True
        with self.assertRaises(Invalid):
            check_cut(g, bad)


if __name__ == '__main__':
    unittest.main()
