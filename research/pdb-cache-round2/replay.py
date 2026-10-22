"""Check pins, rebuild the winning policy and verify the full fixed-graph trace."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import subprocess
import tempfile
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
sys.path[:0]=[str(ROOT),str(P)]
from verifier import load,verify,digest
from search import certificate
from cache_policy import construct,WINNING_POLICY,GRAPH_SHA256

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--record',action='store_true');args=parser.parse_args()
    if not args.record:
        for name,want in load(P/'SOURCES.json')['sha256'].items():
            assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==want,name
    graph=load(ROOT/'benchmarks/graphs/transformer-b4-t128.json');assert digest(graph)==GRAPH_SHA256
    saved=load(P/'certificates/transformer-b4-t128-cap11.json')
    metrics=verify(graph,saved,956301312)
    actions=construct(graph)
    assert actions==saved['actions'],'constructor changed the pinned action trace'
    rebuilt=certificate(graph,actions,956301312,'pdb-marginal-cache-secondary',dict(global_optimal=False,policy=WINNING_POLICY))
    assert metrics==rebuilt['claims']
    assert metrics['peak_bytes']==1441792 and metrics['recompute_cost']==702349312
    with tempfile.TemporaryDirectory(prefix='full-curve-',dir=P) as temporary:
        scratch=Path(temporary)
        calls=[(P/'allocation/allocation_dp.py',scratch/'allocation'),
               (P/'curve-bound/nested_replay.py',scratch/'curve')]
        for driver,out in calls:
            call=subprocess.run([sys.executable,'-B',str(driver),'--out',str(out)],capture_output=True,text=True,timeout=360)
            if call.returncode:raise RuntimeError(str(driver)+'\n'+call.stderr)
        allocation=load(scratch/'allocation/result.json')
        common=load(scratch/'curve/common/RESULTS.json')
        nested=load(scratch/'curve/RESULTS.json')
    assert allocation['status']==common['status']==nested['status']=='PASS'
    rows=common['rows']
    stronger={row['cap_units']:row for row in nested['rows']}
    for row in rows:
        if row['cap_units'] in stronger:
            row['lower_work']=stronger[row['cap_units']]['lower_work']
            row['gap']=row['extra_work']-row['lower_work']
            row['exact_fixed_cap_work']=row['gap']==0
    exact=[row['cap_units'] for row in rows if row['exact_fixed_cap_work']]
    assert len(rows)==69 and exact==nested['exact_caps']==list(range(15,83))
    curve=dict(status='PASS',rows=rows,exact_caps=exact,exact_points=len(exact),
               verified_constructive_points=len(rows),universal_peak_floor=nested['universal_peak_floor'],
               audited_edges=common['lower_audited_edges']+nested['new_audited_edges'],
               additional_fixed_benchmark_wins_from_curve=0)
    result=dict(status='PASS',graph_sha256=digest(graph),claims=metrics,action_trace_reconstructed=True,evidence='author-checked only',global_optimal=False,allocation=allocation,work_curve=curve,nested_proof=nested)
    if args.record:(P/'VERIFY.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)
if __name__=='__main__':main()
