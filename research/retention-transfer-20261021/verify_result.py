"""Standard-library replay of proposed fixed-budget schedule improvements.

Uses the unchanged project verifier, never the optimizer. Does not promote rows.
"""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from verifier import digest, load, require, verify

GRAPH = 'transformer-b4-t128'
GRAPH_HASH = '7d60aaf32c25d4d000872f9d317cdb0cbc71c929307eb69faf7e974c795d5854'
BASE = 'a95cc1588fc57a07cfcf5a350206825e6f5b4b52'


def inside(root, name):
    path = (root / name).resolve()
    require(path.is_relative_to(root.resolve()), 'path outside result root')
    return path


def check_proposal(g, row, proposed, candidate):
    require(g['id'] == GRAPH and digest(g) == GRAPH_HASH, 'wrong frozen graph')
    require(proposed['budget'] == row['budget'], 'wrong fixed budget')
    require(proposed['previous_peak_bytes'] == row['peak_bytes'] and
            proposed['previous_recompute_cost'] == row['recompute_cost'], 'stale incumbent')
    metrics = verify(g, candidate, row['budget'])
    require(metrics['peak_bytes'] == proposed['peak_bytes'] < row['peak_bytes'],
            'not a strict memory improvement')
    require(metrics['recompute_cost'] == proposed['recompute_cost'] <= row['budget'],
            'wrong work or budget overflow')
    require(proposed['global_optimal'] is False, 'unsupported global optimum claim')
    return metrics


def main():
    source = load(HERE / 'SOURCES.json')
    task = load(HERE / 'TASK.json')
    require(source['base_commit'] == task['base_commit'] == BASE, 'base pin mismatch')
    require(task['selection'] == 'explicit-user-followup' and
            task['primary_budget'] == 478150656, 'user-assigned scope mismatch')
    for item in source['repository_inputs']:
        path = inside(ROOT, item['path'])
        require(hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'],
                'pinned input changed: ' + item['path'])
    g = load(ROOT / f'benchmarks/graphs/{GRAPH}.json')
    require(digest(g) == GRAPH_HASH, 'graph hash mismatch')
    rows = {(r['graph'], r['budget']): r for r in load(ROOT / 'records/working-frontiers.json')}
    proposals = load(HERE / 'proposed-frontiers.json')
    require(proposals['graph'] == GRAPH and proposals['graph_sha256'] == GRAPH_HASH and
            proposals['evidence_level'] == 'author-checked', 'proposal scope mismatch')
    checked = []
    seen = set()
    for proposed in proposals['rows']:
        budget = proposed['budget']
        require(budget not in seen, 'duplicate budget proposal')
        seen.add(budget)
        path = inside(ROOT, proposed['object'])
        require(path.is_relative_to(HERE), 'candidate outside package')
        require(hashlib.sha256(path.read_bytes()).hexdigest() == proposed['sha256'],
                'candidate hash mismatch')
        row = rows[GRAPH, budget]
        require(proposed['previous_object'] == row['object'], 'incumbent identity mismatch')
        prior = verify(g, load(ROOT / row['object']), budget)
        require(prior['peak_bytes'] == row['peak_bytes'] and
                prior['recompute_cost'] == row['recompute_cost'], 'incumbent replay mismatch')
        checked.append(dict(budget=budget, **check_proposal(g, row, proposed, load(path))))
    require(task['primary_budget'] in seen, 'primary assigned row missing')
    receipt = load(HERE / 'VERIFY.json')
    require(receipt['status'] == 'PASS' and receipt['evidence_level'] == 'author-checked',
            'invalid verification receipt')
    for name, expected in receipt['artifacts_sha256'].items():
        require(hashlib.sha256(inside(HERE, name).read_bytes()).hexdigest() == expected,
                'package artifact changed: ' + name)
    print(json.dumps(dict(status='PASS', evidence_level='author-checked',
                          results=checked, frontier_records_changed=False,
                          scope='frozen-graph fixed-budget replay; independent review pending')))


if __name__ == '__main__':
    main()
