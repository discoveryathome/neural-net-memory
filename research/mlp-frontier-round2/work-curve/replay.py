"""Reconstruct both complete MLP fixed-memory work curves from compact steps."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(HERE.parent), str(ROOT)]
from chain_exact import Limited, solve
from verifier import digest, load, verify

ORIGINAL = {
    'mlp-b4': [(0,37),(2129920,21),(4259840,13),(8519680,11),(17039360,10)],
    'mlp-b8': [(0,73),(4259840,33),(8519680,17),(17039360,13),(34078720,10)],
}


def graph_facts(graph, expected):
    assert digest(graph) == expected['graph_sha256']
    unit = 4096
    assert graph['inputs'] == [dict(id='x', bytes=unit)]
    assert all(v['bytes'] % unit == 0 for v in graph['nodes'])
    for i, node in enumerate(graph['nodes']):
        parent = graph['nodes'][i-1]['id'] if i else 'x'
        assert node['deps'] == node['backward_requires'] == [parent]
    floor = (unit + graph['nodes'][0]['bytes'] + graph['nodes'][1]['bytes']) // unit
    assert graph['nodes'][1]['deps'] == [graph['nodes'][0]['id']] and floor == 9
    zero = sum(v['bytes'] for v in graph['inputs'] + graph['nodes']) // unit
    assert zero == expected['zero_work_cap_units']
    steps = expected['steps']
    assert steps[0][0] == floor and steps[-1] == [zero, 0]
    assert all(b[0] > a[0] and b[1] < a[1] for a, b in zip(steps, steps[1:]))
    return unit, floor, zero


def run(repo, out):
    repo, out = Path(repo).resolve(), Path(out).resolve()
    if repo != ROOT.resolve():
        raise ValueError('repo must be the checkout containing this package')
    out.mkdir(parents=True, exist_ok=True)
    for name, wanted in load(HERE/'SOURCES.json')['sha256'].items():
        assert hashlib.sha256((repo/name).read_bytes()).hexdigest() == wanted, name
    expected = load(HERE/'EXPECTED.json')
    began = time.monotonic()
    deadline = began + 120

    def allowance():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise Limited('aggregate120second limit; no complete curve claim')
        return min(30, remaining)

    def event(item):
        item = dict(item, source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
        with (out/'measurements.jsonl').open('a') as handle:
            handle.write(json.dumps(item, sort_keys=True)+'\n')

    families, nonzero_exclusions, original_replays = {}, 0, 0
    for name, want in expected['families'].items():
        graph = load(repo/f'benchmarks/graphs/{name}.json')
        unit, floor, zero = graph_facts(graph, want)
        absent, below = solve(graph, (floor-1)*unit, 10**12,
                              state_cap=250000, seconds=allowance())
        assert absent is None and below['status'] == 'infeasible_at_budget'
        # The universal exclusion is the mandatory first UP/GELU allocation,
        # not the finite diagnostic budget used by the preceding search.
        rows, last, step = [], None, 0
        for cap in range(floor, zero+1):
            while step+1 < len(want['steps']) and want['steps'][step+1][0] <= cap:
                step += 1
            work = want['steps'][step][1]
            event(dict(stage='positive_start', graph=name, cap_units=cap, budget=work))
            witness, positive = solve(graph, cap*unit, work,
                                       state_cap=250000, seconds=allowance())
            assert witness is not None and positive['status'] == 'optimal'
            metrics = verify(graph, witness, work)
            assert metrics['peak_bytes'] <= cap*unit and metrics['recompute_cost'] == work
            witness['metadata'].update(auxiliary_work_curve=True,
                evidence='author-checked only; scientific acceptance pending',
                author='Codex AI for @0xqtpie',
                credit='Doug Colkitt / @Mister-Meeseeks model/verifier/trial; PR6 regional predecessor; parent exact-chain work')
            path = out/f'{name}-cap{cap}.json'
            path.write_text(json.dumps(witness, indent=2)+'\n')
            negative = None
            if work:
                absent, negative = solve(graph, cap*unit, work-1,
                                          state_cap=250000, seconds=allowance())
                assert absent is None and negative['status'] == 'infeasible_at_budget'
                nonzero_exclusions += 1
            else:
                assert cap == zero and metrics['peak_bytes'] == cap*unit
                assert sum(a['op'] == 'forward' for a in witness['actions']) == len(graph['nodes'])
            budgets = []
            for budget, target in ORIGINAL[name]:
                if target == cap:
                    original = copy.deepcopy(witness); original['budget'] = budget
                    assert verify(graph, original, budget) == metrics
                    budgets.append(budget); original_replays += 1
            row = dict(cap_units=cap, peak_cap_bytes=cap*unit, minimum_work=work,
                       verified_metrics=metrics, positive=positive, work_minus_one=negative,
                       actions_sha256=digest(witness['actions']), certificate_file=path.name,
                       original_budget_replays=budgets)
            rows.append(row); last = witness
            event(dict(stage='completed_cap', graph=name, **row))
            allowance()
        assert len(rows) == zero-floor+1
        changed = copy.deepcopy(graph); changed['nodes'][0]['cost'] += 1
        try:
            graph_facts(changed, want)
        except AssertionError:
            foreign_rejected = True
        else:
            raise AssertionError('changed frozen graph accepted')
        changed = copy.deepcopy(graph); changed['nodes'][2]['backward_requires'] = ['x']
        try:
            solve(changed, zero*unit, 0, state_cap=250000, seconds=allowance())
        except ValueError:
            unsupported_rejected = True
        else:
            raise AssertionError('non-parent saved requirement accepted')
        families[name] = dict(graph_sha256=digest(graph), rows=rows, steps=want['steps'],
            universal_peak_floor=dict(units=floor, bytes=floor*unit,
                reason='standing immutable x plus mandatory UP input and GELU output coexist before any drop',
                below_floor_search=below, applies_at_every_work_budget=True),
            zero_work_cap_units=zero, zero_work_peak_bytes=zero*unit,
            negative_controls=dict(changed_frozen_graph_rejected=foreign_rejected,
                                   unsupported_saved_requirement_rejected=unsupported_rejected))
    assert sum(len(v['rows']) for v in families.values()) == 94
    assert sum(len(v['steps']) for v in families.values()) == 34
    assert nonzero_exclusions == 92 and original_replays == 10
    result = dict(status='PASS',schema='mlp-complete-work-curves/v1',unit_bytes=4096,
        families=families,verified_cap_points=94,nondominated_steps=34,
        work_minus_one_exclusions=nonzero_exclusions,original_budget_replays=original_replays,
        additional_original_benchmark_wins_from_curve=0,seconds=time.monotonic()-began,
        limits=dict(states_per_query=250000,seconds_per_query=30,aggregate_seconds=120),
        scope='Complete fixed-cap minimum-work functions, including all finite-cap plateaus, a universal9u floor, and zero-work tails. Auxiliary points are not added original benchmark cases.',
        evidence='author-checked exact-state computations and mathematical normalization; same-author-team review is not independent scientific acceptance')
    (out/'RESULTS.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=ROOT)
    parser.add_argument('--out', type=Path, default=HERE/'generated')
    args = parser.parse_args()
    result = run(args.repo, args.out)
    print(json.dumps({k:result[k] for k in ['status','verified_cap_points','nondominated_steps','work_minus_one_exclusions','original_budget_replays','seconds']}), flush=True)


if __name__ == '__main__':
    main()
