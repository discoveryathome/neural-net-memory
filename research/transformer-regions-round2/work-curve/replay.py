"""Reconstruct every nondominated point of the frozen one-block work curve."""
import argparse
import json
from pathlib import Path
import sys
import time

P=Path(__file__).resolve().parent
PACKAGE=P.parent
ROOT=P.parents[2]
sys.path[:0]=[str(PACKAGE),str(ROOT)]
from regional_exact import solve
from verifier import digest,load,verify


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,default=P/'generated')
    args=parser.parse_args()
    graph=load(ROOT/'benchmarks/graphs/transformer-b1-t32.json')
    pins=load(PACKAGE/'SOURCES.json')['frozen_repository_files']
    import hashlib
    filename='benchmarks/graphs/transformer-b1-t32.json'
    assert hashlib.sha256((ROOT/filename).read_bytes()).hexdigest()==pins[filename]
    expected=load(P/'EXPECTED.json')
    unit=expected['unit_bytes']
    assert graph['id']==expected['graph']
    assert all(v['bytes']%unit==0 for v in graph['inputs']+graph['nodes'])
    nodes={v['id']:v for v in graph['nodes']}
    assert sum(v['bytes'] for v in graph['inputs'])==unit
    assert nodes['b0_gelu']['deps']==['b0_up']
    assert nodes['b0_up']['bytes']==nodes['b0_gelu']['bytes']==4*unit
    args.out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for units,work in expected['rows']:
        start=time.monotonic()
        positive=solve(graph,units*unit,53231616,states=500000,seconds=15)
        assert positive is not None
        metrics=verify(graph,positive,53231616)
        assert metrics['peak_bytes']==units*unit and metrics['recompute_cost']==work
        if work:
            assert solve(graph,units*unit,work-1,states=500000,seconds=15) is None
        (args.out/f'cap{units}.json').write_text(json.dumps(positive,indent=2)+'\n')
        rows.append(dict(cap_units=units,peak_bytes=units*unit,minimum_work=work,
                         negative='EXHAUSTED' if work else 'nonnegative work',
                         states=positive['metadata']['states'],seconds=time.monotonic()-start))
    assert [r['cap_units'] for r in rows]==list(range(9,20))
    assert all(a['minimum_work']>b['minimum_work'] for a,b in zip(rows,rows[1:]))
    result=dict(status='PASS',graph_sha256=digest(graph),rows=rows,
                scope='complete frozen one-block memory/work Pareto curve',evidence='author-checked only')
    (args.out/'RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    main()
