"""Check the same auxiliary 12-unit trace at its exact work allowance."""
import copy
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from verifier import Invalid, digest, load, verify


def run():
    graph = load(ROOT/'benchmarks/graphs/transformer-b4-t128.json')
    assert digest(graph) == '7d60aaf32c25d4d000872f9d317cdb0cbc71c929307eb69faf7e974c795d5854'
    source = HERE/'controls/traces/auxiliary-12u-retimed.json'
    assert hashlib.sha256(source.read_bytes()).hexdigest() == 'ac13fd9bf91202661b265c97b6f84cac55c6ad509afd5ecd525d660ed86a2c6b'
    old = load(source)
    exact = load(HERE/'controls/auxiliary12-exact-work-budget.json')
    assert old['budget'] == 600000000 and exact['budget'] == 540246016
    assert old['actions'] == exact['actions'] and old['claims'] == exact['claims']
    old_metrics = verify(graph, old, 600000000)
    metrics = verify(graph, exact, 540246016)
    assert metrics == old_metrics
    assert metrics['peak_bytes'] == 1572864 and metrics['recompute_cost'] == 540246016
    bad = copy.deepcopy(exact)
    bad['budget'] = 478150656
    try:
        verify(graph, bad, 478150656)
    except Invalid as error:
        assert 'recomputation budget exceeded' in str(error), str(error)
        rejection = str(error)
    else:
        raise AssertionError('original middle-budget control unexpectedly accepted')
    return dict(status='PASS', source_allowance=600000000,
                exact_allowance=540246016, original_middle_allowance=478150656,
                metrics=metrics, identical_actions=True,
                actions_sha256=digest(exact['actions']),
                original_budget_rejected=rejection,
                evidence='author-checked auxiliary construction; no additional original benchmark win')


if __name__ == '__main__':
    print(json.dumps(run(), sort_keys=True))
