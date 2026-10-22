"""Replay the exact ResNet staircase and its fixed-budget consequences."""
import argparse
import copy
import hashlib
import json
import platform
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from chain_exact import solve
from verifier import digest, load, verify

UNIT = 262144
CEILING = 605552640
GRAPH_HASH = 'fe120b9dbba356bf53b6042ad7174fd2506df22906c017502008405f9c0f354f'
TABLE = [(4, 378339328), (5, 189136896), (6, 151257088),
         (7, 113442816), (8, 75628544), (9, 37814272), (10, 0)]


def replay(write=False):
    if not write:
        for item in load(HERE/'SOURCES.json')['repository_inputs']:
            assert hashlib.sha256((ROOT/item['path']).read_bytes()).hexdigest() == item['sha256'], item['path']
    graph = load(ROOT/'benchmarks/graphs/resnet-b4-c32.json')
    assert digest(graph) == GRAPH_HASH
    assert all(v['bytes'] == UNIT for v in graph['inputs']+graph['nodes'])
    # b1_add has three distinct internal deps/output allocations, plus immutable x.
    add = next(v for v in graph['nodes'] if v['id'] == 'b1_add')
    local_names = set(add['deps']) | {add['id']} | {v['id'] for v in graph['inputs']}
    sizes = {v['id']: v['bytes'] for v in graph['inputs']+graph['nodes']}
    assert sum(sizes[v] for v in local_names) == 4*UNIT
    cases = []
    for allocations, expected in TABLE:
        cap = allocations*UNIT
        stats, result = solve(graph, cap, CEILING, max_states=250000, seconds=30)
        assert result is not None and stats['status'] == 'OPTIMAL'
        assert result['claims']['recompute_cost'] == expected
        assert result['claims']['peak_bytes'] == cap
        verify(graph, result, CEILING)
        path = HERE/'certificates'/f'resnet-b4-c32-cap{allocations}.json'
        if write:
            path.parent.mkdir(exist_ok=True)
            c = copy.deepcopy(result)
            c['budget'] = expected
            c['metadata']['search_budget'] = CEILING
            c['metadata']['witness_budget'] = expected
            verify(graph, c, expected)
            path.write_text(json.dumps(c, indent=2)+'\n')
        stored = load(path)
        verify(graph, stored, expected)
        assert stored['actions'] == result['actions']
        assert stored['claims'] == result['claims']
        item = dict(allocations=allocations, cap_bytes=cap, minimum_recompute_cost=expected,
                    certificate=str(path.relative_to(ROOT)),
                    certificate_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), search=stats)
        if expected:
            negative, candidate = solve(graph, cap, expected-1, max_states=250000, seconds=30)
            assert candidate is None and negative['status'] == 'INFEASIBLE'
            item['threshold_minus_one'] = negative
        cases.append(item)
    # Derive the objective at every original fixed budget, and verify incumbents
    # unchanged. The three formerly open rows acquire matching exact lower bounds.
    consequences = []
    for row in load(ROOT/'records/working-frontiers.json'):
        if row['graph'] != graph['id']:
            continue
        optimum = min(k*UNIT for k, cost in TABLE if cost <= row['budget'])
        assert optimum == row['peak_bytes']
        verify(graph, load(ROOT/row['object']), row['budget'])
        consequences.append(dict(graph=graph['id'], budget=row['budget'],
                                 peak_bytes=optimum, prior_lower_bound=row['lower_bound'],
                                 previously_open=not row['optimal'],
                                 conclusion='unchanged witness meets exact computational optimum'))
    # Known smaller ResNet is a falsification control for the domain reductions.
    secondary = load(HERE/'SECONDARY-WORK.json')
    for row in secondary:
        prior = next(v for v in load(ROOT/'records/working-frontiers.json')
                     if v['graph']==graph['id'] and v['budget']==row['budget'])
        assert prior['peak_bytes']==row['peak_bytes']
        assert prior['recompute_cost']==row['prior_work']
        path = ROOT/row['object']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
        witness = load(path)
        metrics = verify(graph,witness,row['budget'])
        cap = row['peak_bytes']//UNIT
        assert metrics['recompute_cost']==dict(TABLE)[cap]==row['new_work']<row['prior_work']
        assert metrics['peak_bytes']==row['peak_bytes']
        assert witness['actions']==load(HERE/'certificates'/f'resnet-b4-c32-cap{cap}.json')['actions']
    assert len(secondary)==2
    small = load(ROOT/'benchmarks/graphs/resnet-b2-c32.json')
    small_cases = []
    for cap, budget, expected in [(4*UNIT, 37847040, None), (4*UNIT, 75694080, 75628544)]:
        stats, c = solve(small, cap, budget, max_states=250000, seconds=30)
        if expected is None:
            assert c is None and stats['status'] == 'INFEASIBLE'
        else:
            verify(small, c, budget)
            assert c['claims']['recompute_cost'] == expected
        small_cases.append(stats)
    result = dict(model=graph['model'], graph=graph['id'], graph_sha256=GRAPH_HASH,
                  evidence_level='author-checked', local_allocation_lower_bound=4*UNIT,
                  staircase=cases, fixed_budget_consequences=consequences,
                  secondary_work_gains=secondary,
                  smaller_resnet_controls=small_cases,
                  resource_caps=dict(states_per_call=250000, seconds_per_call=30),
                  environment=dict(python=platform.python_version(), platform=platform.platform()))
    if write:
        (HERE/'RESULTS.json').write_text(json.dumps(result, indent=2)+'\n')
    else:
        saved = load(HERE/'RESULTS.json')
        assert saved['graph_sha256'] == result['graph_sha256']
        assert saved['fixed_budget_consequences'] == consequences
        assert [(r['cap_bytes'], r['minimum_recompute_cost'], r['certificate_sha256']) for r in saved['staircase']] == [(r['cap_bytes'], r['minimum_recompute_cost'], r['certificate_sha256']) for r in cases]
    print(json.dumps(dict(status='PASS', staircase_points=len(cases),
                          formerly_open_cells_settled=sum(v['previously_open'] for v in consequences),
                          fixed_budget_peak_improvements=0,
                          fixed_peak_work_improvements=len(secondary),
                          max_records=max(v['search']['states'] for v in cases),
                          all_witnesses_verified=True), sort_keys=True))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='regenerate package outputs')
    replay(parser.parse_args().write)
