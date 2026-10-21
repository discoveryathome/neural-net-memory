"""Replay the proposed cut, fixed witnesses, auxiliary challenge and input pins.

This checks the result package; it does not promote any frontier row.
"""
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from verifier import digest, load, require, verify
from reset_cut import check_cut, find_cut
from budget_cut import check_budget_proof,make_budget_proof


def validate_selection(task, root):
    seed = task.get('seed')
    require(isinstance(seed, str) and re.fullmatch('[0-9a-fA-F]{32}', seed), 'invalid seed')
    catalog = load(root / 'discover/catalog.json')

    def draw(tracks):
        word = int(seed[:8], 16) % sum(t['weight'] for t in tracks)
        for track in tracks:
            word -= track['weight']
            if word < 0:
                chosen = track['tasks'][int(seed[8:16], 16) % len(track['tasks'])]
                return track, chosen
        raise AssertionError('track weights do not cover draw')

    track, card = draw(catalog['tracks'])
    require(task['original_draw'] == dict(track=track['id'], task=card['id']),
            'original picker draw mismatch')
    numerical = [t for t in catalog['tracks'] if t['id'] in ('schedule-search', 'bounds')]
    track, card = draw(numerical)
    change = task['scope_change']
    require(change['restriction'] == [t['id'] for t in numerical] and
            change['relative_weights'] == [t['weight'] for t in numerical] and
            change['first_word_mod_55'] == int(seed[:8], 16) % sum(t['weight'] for t in numerical),
            'numerical-track projection mismatch')
    require(change['track'] == track['id'] and change['task'] == card['id'],
            'projected card mismatch')
    where = card['rows'].get('where', {})
    rows = [r for r in load(root / 'records/working-frontiers.json')
            if (not card['rows'].get('open', True) or not r['optimal']) and
            all(str(r[k]) == str(v) for k, v in where.items())]
    row = rows[int(seed[16:24], 16) % len(rows)]
    require(task['graph'] == row['graph'] and task['selected_budget'] == row['budget'],
            'projected row mismatch')
    require(task['starting_peak_bytes'] == row['peak_bytes'] and
            task['starting_lower_bound_bytes'] == row['lower_bound'], 'starting row mismatch')
    require(task['graph_path'] == f"benchmarks/graphs/{row['graph']}.json", 'graph path mismatch')


def main():
    task = load(HERE / 'TASK.json')
    source = load(HERE / 'SOURCES.json')
    for item in source['repository_inputs']:
        path = (ROOT / item['path']).resolve()
        require(path.is_relative_to(ROOT.resolve()), 'source path outside repository')
        require(hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'],
                'pinned predecessor changed: ' + item['path'])
    require(source['base_commit'] == task['base_commit'], 'base provenance mismatch')
    validate_selection(task, ROOT)
    graph = load(ROOT / task['graph_path'])
    require(digest(graph) == task['graph_sha256'], 'task graph identity mismatch')
    proof = load(HERE / 'cut.json')
    floor = check_cut(graph, proof)
    require(find_cut(graph) == proof, 'cut reconstruction differs')
    budget_proof=load(HERE/'budget-cut.json')
    budget_result=check_budget_proof(graph,budget_proof)
    require(make_budget_proof(graph)==budget_proof,'budget proof reconstruction differs')
    def bound_at(budget):
        return budget_result['memory_bound_bytes'] if budget<budget_result['extra_work_lower_bound'] else floor
    rows = {(r['graph'], r['budget']): r for r in load(ROOT / 'records/working-frontiers.json')}
    proposals = load(HERE / 'proposed-bounds.json')
    require(proposals['evidence_level'] == 'author-checked', 'wrong evidence level')
    require(proposals['graph_sha256'] == digest(graph), 'proposal graph mismatch')
    require(proposals['graph'] == graph['id'] and proposals['model'] == graph['model'],
            'proposal identity mismatch')
    require(task['proposed_lower_bound_bytes'] == bound_at(task['selected_budget']), 'task bound mismatch')
    require(task['all_budget_lower_bound_bytes']==floor,'all-budget floor mismatch')
    require(task['minimum_extra_work_at_ten_chunks']==budget_result['extra_work_lower_bound'],
            'task work threshold mismatch')
    require(proposals['minimum_extra_work_at_ten_chunks']==budget_result['extra_work_lower_bound'] and
            proposals['all_budget_lower_bound_bytes']==floor, 'proposal threshold/floor mismatch')
    checked = []
    for proposed in proposals['rows']:
        row = rows[graph['id'], proposed['budget']]
        bound=bound_at(proposed['budget'])
        require(proposed['previous_lower_bound_bytes'] == row['lower_bound'], 'stale starting bound')
        require(proposed['proposed_lower_bound_bytes'] == bound > row['lower_bound'],
                'proposal must strictly strengthen a working bound')
        witness = load(ROOT / row['object'])
        metrics = verify(graph, witness, row['budget'])
        require(metrics['peak_bytes'] == proposed['existing_witness_peak_bytes'] == row['peak_bytes'],
                'stale witness peak')
        require(bound <= metrics['peak_bytes'], 'cut contradicts a fixed witness')
        require(type(proposed['proposed_optimal']) is bool and
                proposed['proposed_optimal']==(bound==metrics['peak_bytes']), 'optimality proposal mismatch')
        checked.append(row['budget'])
    expected = [r['budget'] for r in rows.values()
                if r['graph'] == graph['id'] and r['lower_bound'] < bound_at(r['budget'])]
    require(checked == expected, 'affected-row coverage mismatch')
    require(task['selected_budget'] in checked, 'selected row missing')
    auxiliary = load(HERE / 'certificates/auxiliary-budget.json')
    extra = task['auxiliary_budget']
    metrics = verify(graph, auxiliary, extra)
    require(metrics['peak_bytes'] == floor, 'auxiliary witness does not attain all-budget memory floor')
    require(metrics['recompute_cost'] == extra > task['selected_budget'],
            'auxiliary challenge must be marked outside selected budget')
    require(extra>=budget_result['extra_work_lower_bound'],'auxiliary witness contradicts work bound')
    receipt = load(HERE / 'VERIFY.json')
    require(receipt['status'] == 'PASS' and receipt['evidence_level'] == 'author-checked',
            'incorrect verification receipt status')
    for name, expected_hash in receipt['artifacts_sha256'].items():
        path = (HERE / name).resolve()
        require(path.is_relative_to(HERE.resolve()), 'artifact path outside package')
        require(hashlib.sha256(path.read_bytes()).hexdigest() == expected_hash,
                'package artifact changed: ' + name)
    print(json.dumps(dict(status='PASS', proposed_lower_bound_bytes=bound_at(task['selected_budget']),
                          all_budget_floor_bytes=floor,
                          minimum_extra_work_at_ten_chunks=budget_result['extra_work_lower_bound'],
                          affected_fixed_budgets=checked,
                          auxiliary_peak_bytes=metrics['peak_bytes'],
                          auxiliary_extra_cost=extra,
                          scope='Author-checked cut/witness replay and pinned input consistency; '
                                'independent mathematical review remains open')))


if __name__ == '__main__':
    main()
