"""Compile, generate/audit heuristics, and check the complete 10u exclusion.

Run inside the contributor's execution sandbox. All generated files stay in --out.
The native executable and generated binary proof/table files are not source files.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

P=Path(__file__).resolve().parent
ROOT=P.parents[1]
sys.path.insert(0,str(ROOT))
from verifier import digest,load,validate_graph,verify

GRAPH_SHA='7d60aaf32c25d4d000872f9d317cdb0cbc71c929307eb69faf7e974c795d5854'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=P/'generated')
    parser.add_argument('--skip-controls',action='store_true',help='omit the additional random/tiny/positive controls, never the complete proof checks')
    args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    tmp=out/'tmp';tmp.mkdir(exist_ok=True)
    env=dict(os.environ,TMPDIR=str(tmp),NATIVE_PROOF_OUT=str(out))
    began=time.monotonic()
    def call(argv,name,timeout=90):
        result=subprocess.run(list(map(str,argv)),cwd=ROOT,env=env,capture_output=True,text=True,timeout=timeout)
        (out/(name+'.log')).write_text(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError((name,result.returncode,result.stdout,result.stderr))
        return result.stdout
    direct=Path('/Library/Developer/CommandLineTools/usr/bin/clang++')
    compiler=str(direct) if direct.exists() else shutil.which('c++')
    if compiler is None:raise RuntimeError('C++17 compiler unavailable; no proof run')
    flags=['-std=c++17','-O3','-DNDEBUG']
    sdk=Path('/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk')
    if sys.platform=='darwin' and sdk.exists():flags=['-isysroot',str(sdk)]+flags
    executable=out/'native_search'
    call([compiler,*flags,P/'native_search.cpp','-o',executable],'compile')
    call([sys.executable,'-B',P/'pdb/replay_pdb.py','--repo',ROOT,'--out',out/'pdb','--cap-units','10'],'pdb',timeout=120)
    graph=load(ROOT/'benchmarks/graphs/transformer-b4-t128.json')
    validate_graph(graph);assert digest(graph)==GRAPH_SHA
    ns=graph['nodes'];names=[v['id'] for v in ns];index={v:i for i,v in enumerate(names)}
    mask=lambda values:sum(1<<index[v] for v in values if v in index)
    quantum=131072
    assert graph['inputs']==[{'id':'x','bytes':quantum}] and len(ns)==56
    assert all(v['bytes'] in (quantum,4*quantum) and v['recomputable'] for v in ns)
    order=names.copy()
    for block in range(4):
        v=f'b{block}_v';order.remove(v);order.insert(order.index(f'b{block}_probs')+1,v)
    pivot=index['b3_gelu'];ancestors={pivot};todo=[pivot]
    while todo:
        for dep in ns[todo.pop()]['deps']:
            if dep in index and index[dep] not in ancestors:ancestors.add(index[dep]);todo.append(index[dep])
    assert ancestors==set(range(54))=={index[v] for v in order[:54]}
    assert order[54:]==['b3_down','b3_residual2']
    forced=mask(['b3_up','b3_gelu'])
    options=[i for i in range(54) if ns[i]['bytes']==quantum]
    seeds=[(forced,0,54,0)]+[(forced|(1<<i),0,54,0) for i in options]
    assert len(seeds)==39
    lines=['56 1 10 956301312 1000000 30 1 0']
    for v in ns:
        children=mask(w['id'] for w in ns if v['id'] in w['deps'])
        lines.append(f'{v["id"]} {v["bytes"]//quantum} {v["cost"]} {mask(v["deps"])} {mask(v["backward_requires"])} {children} 1')
    lines+=[' '.join(str(index[v]) for v in order),str(mask(graph['outputs'])),str(len(seeds))]
    lines+=[' '.join(map(str,seed)) for seed in seeds]
    back=out/'pdb/b4-backward-pdb-cap10.json';demand=out/'pdb/b4-output-demand-pdb-cap10.json'
    bm=load(back);dm=load(demand)
    lines += [f'{len(bm["done_masks"])} 4096 32768',' '.join(map(str,bm['done_masks'])),'16384 32768']
    inp=out/'critical-cap10.input';inp.write_text('\n'.join(lines)+'\n')
    labels=out/'closed-labels.bin'
    native=json.loads(call([executable,inp,back.with_suffix('.bin'),demand.with_suffix('.bin'),labels],'native',timeout=45))
    assert native['status']=='EXHAUSTED_FIXED_ORDER' and native['queue']==0
    assert native['states']==native['expanded']==native['closed_label_rows']==419463
    assert native['generated']==10474740
    from check_closed import check
    # The checker is separately authored and regenerates every reduced edge.
    receipt=check(inp,labels,back,demand)
    (out/'closure-check.json').write_text(json.dumps(receipt,indent=2)+'\n')
    call([sys.executable,'-B',P/'negative_controls.py','--out',out],'proof-negatives')
    upper=load(ROOT/'research/trial-30m/certificates/transformer-b4-t128-b956301312-p1441792.json')
    metrics=verify(graph,upper,956301312)
    assert metrics['peak_bytes']==1441792 and metrics['recompute_cost']==737935360
    if not args.skip_controls:
        call([sys.executable,'-B',P/'check_native.py'],'random-differential',timeout=120)
        call([sys.executable,'-B',P/'native_driver.py','--controls'],'tiny-controls',timeout=120)
        call([sys.executable,'-B',P/'pdb/replay_pdb.py','--repo',ROOT,'--out',out/'pdb13','--cap-units','13'],'pdb13',timeout=120)
        prefix=P/'controls/known13.json'
        call([sys.executable,'-B',P/'native_driver.py','--cap','1703936','--budget','478150656','--states','1000000','--seconds','30','--demand-mode','1','--prefix-from',prefix,'--pdb',out/'pdb13/b4-backward-pdb-cap13.json','--demand-pdb',out/'pdb13/b4-output-demand-pdb-cap13.json'],'positive13-control',timeout=45)
    result=dict(status='PASS',evidence='author-checked; separate implementation checks within the author team; scientific acceptance pending',
                graph_sha256=GRAPH_SHA,budget=956301312,excluded_peak_bytes=1310720,
                matching_upper_peak_bytes=1441792,upper_recompute_cost=737935360,
                compiler=compiler,flags=flags,python=sys.version,seconds=time.monotonic()-began,
                native=native,closure=receipt,
                source_sha256=hashlib.sha256((P/'native_search.cpp').read_bytes()).hexdigest(),
                executable_sha256=hashlib.sha256(executable.read_bytes()).hexdigest(),
                labels_sha256=hashlib.sha256(labels.read_bytes()).hexdigest())
    (out/'replay-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)

if __name__=='__main__':main()
