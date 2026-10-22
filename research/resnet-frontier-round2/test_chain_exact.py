"""Differential controls against unmodified, unreduced minimax enumeration."""
import copy
import random
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from chain_exact import Limited, solve
from search import exact
from verifier import Invalid, load, verify


def synthetic(seed, n):
    rng = random.Random(seed)
    nodes = []
    for i in range(n):
        prev = 'x' if i == 0 else f'v{i-1}'
        names = ['x']+[f'v{j}' for j in range(i+1)]
        deps = [prev]
        if i > 1 and rng.random() < .55:
            extra = rng.choice(names[:-1])
            if extra not in deps:
                deps.append(extra)
        nodes.append(dict(id=f'v{i}', deps=deps, bytes=rng.randint(1, 5),
                          cost=rng.randint(1, 4), backward_cost=1,
                          backward_requires=rng.sample(names, rng.randrange(min(3, len(names))+1)),
                          recomputable=rng.random() > .2))
    return dict(model='activation-memory/v1', id=f'chain-control-{seed}',
                inputs=[dict(id='x', bytes=rng.randint(1, 4))], nodes=nodes,
                outputs=[f'v{n-1}'])


class Differential(unittest.TestCase):
    def test_120_nonuniform_random_chain_budget_pairs(self):
        # Includes skips, non-recomputable values, ancestor/self/empty saved
        # requirements, nonuniform costs and bytes, and several external sizes.
        for seed in range(40):
            graph = synthetic(197327+seed, 3+seed % 3)
            for budget in (0, 3, 9):
                with self.subTest(seed=seed, budget=budget):
                    reference = exact(graph, budget)
                    optimum = reference['claims']['peak_bytes']
                    stats, candidate = solve(graph, optimum, budget)
                    self.assertIsNotNone(candidate)
                    verify(graph, candidate, budget)
                    self.assertEqual(candidate['claims']['peak_bytes'], optimum)
                    _, unpruned = solve(graph, optimum, budget, astar=False, use_lower_bound=False)
                    self.assertEqual(candidate['claims']['recompute_cost'], unpruned['claims']['recompute_cost'])
                    stats, candidate = solve(graph, optimum-1, budget)
                    self.assertEqual(stats['status'], 'INFEASIBLE')
                    self.assertIsNone(candidate)

    def test_all_tiny_chain_controls(self):
        rows = load(ROOT/'records/working-frontiers.json')
        controls = 0
        for row in rows:
            graph = load(ROOT/f"benchmarks/graphs/{row['graph']}.json")
            if row['family'] != 'synthetic' or len(graph['nodes']) > 12 or any(graph['nodes'][i-1]['id'] not in graph['nodes'][i]['deps'] for i in range(1, len(graph['nodes']))):
                continue
            controls += 1
            optimum = exact(graph, row['budget'])['claims']['peak_bytes']
            stats, c = solve(graph, optimum, row['budget'])
            self.assertEqual(c['claims']['peak_bytes'], optimum)
            stats, c = solve(graph, optimum-1, row['budget'])
            self.assertIsNone(c)
            self.assertEqual(stats['status'], 'INFEASIBLE')
        self.assertGreaterEqual(controls, 5)

    def test_b2_resnet_settled_controls(self):
        graph = load(ROOT/'benchmarks/graphs/resnet-b2-c32.json')
        stats, c = solve(graph, 4*262144, 75694080)
        self.assertEqual(c['claims']['recompute_cost'], 75628544)
        self.assertEqual(c['claims']['peak_bytes'], 1048576)
        stats, c = solve(graph, 4*262144, 37847040)
        self.assertIsNone(c)
        self.assertEqual(stats['status'], 'INFEASIBLE')

    def test_unnormalized_full_resnet_controls(self):
        from reference_fixed_cap import solve as unnormalized
        graph = load(ROOT/'benchmarks/graphs/resnet-b4-c32.json')
        for cap, budget, expected in [(1048576, 605552640, 378339328),
                                      (1048576, 302776320, None),
                                      (1310720, 151388160, None)]:
            cost, stats = unnormalized(graph, cap, budget, limit=200000, seconds=30)
            self.assertEqual(cost, expected)

    def test_transient_output_allocation(self):
        graph = dict(model='activation-memory/v1', id='allocation-control',
                     inputs=[dict(id='x', bytes=5)],
                     nodes=[dict(id='y', deps=['x'], bytes=7, cost=1, backward_cost=1,
                                 backward_requires=[], recomputable=True)], outputs=['y'])
        stats, c = solve(graph, 11, 0)
        self.assertIsNone(c)
        stats, c = solve(graph, 12, 0)
        self.assertEqual(c['claims']['peak_bytes'], 12)

    def test_resource_and_domain_fail_closed(self):
        graph = synthetic(0, 5)
        with self.assertRaises(Limited):
            solve(graph, 100, 100, max_states=1)
        with self.assertRaises(Limited):
            solve(graph, 100, 100, seconds=1e-20)
        bad = copy.deepcopy(graph)
        bad['nodes'][2]['deps'] = ['x']
        with self.assertRaises(ValueError):
            solve(bad, 100, 100)
        for kwargs in (dict(cap=True, budget=0), dict(cap=0, budget=-1),
                       dict(cap=100, budget=0, seconds=float('inf'))):
            with self.assertRaises(ValueError):
                solve(graph, **kwargs)


if __name__ == '__main__':
    unittest.main()
