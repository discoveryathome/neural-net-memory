"""Check the 12-unit peak exclusion and the 13/14-unit work optima."""
import argparse
import hashlib
import itertools
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
    parser.add_argument('--prepare-only',action='store_true',help='generate the artifacts and controls but omit closure checking; this is not a completed proof replay')
    args=parser.parse_args()
    pins=load(P/'SOURCE.json')
    for name,wanted in pins['core_files'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==wanted,name
    for name,wanted in pins['package_files'].items():
        assert hashlib.sha256((P/name).read_bytes()).hexdigest()==wanted,name
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    tmp=out/'tmp';tmp.mkdir(exist_ok=True)
    env=dict(os.environ,TMPDIR=str(tmp),NATIVE_PROOF_OUT=str(out))
    began=time.monotonic()
    def call(argv,name,timeout=120):
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
    # These copied source files are self-contained; no installed package or PR
    # checkout is imported. Their auditors reconstruct every pattern edge.
    call([sys.executable,'-B',P/'pdb/replay_pdb.py','--repo',ROOT,'--out',out/'pdb','--cap-units','12'],'pdb12')
    call([sys.executable,'-B',P/'pdb/replay_terminal.py','--repo',ROOT,'--out',out/'pdb'],'terminal-pdbs')
    graph=load(ROOT/'benchmarks/graphs/transformer-b4-t128.json')
    validate_graph(graph);assert digest(graph)==GRAPH_SHA
    ns=graph['nodes'];names=[v['id'] for v in ns];index={v:i for i,v in enumerate(names)}
    mask=lambda values:sum(1<<index[v] for v in set(values) if v in index)
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
    seeds=[(forced|sum(1<<i for i in chosen),0,54,0) for count in range(4) for chosen in itertools.combinations(options,count)]
    assert len(seeds)==9178
    lines=['56 1 12 478150656 10000000 120 1 0']
    for v in ns:
        children=mask(w['id'] for w in ns if v['id'] in w['deps'])
        lines.append(f'{v["id"]} {v["bytes"]//quantum} {v["cost"]} {mask(v["deps"])} {mask(v["backward_requires"])} {children} 1')
    lines+=[' '.join(str(index[v]) for v in order),str(mask(graph['outputs'])),str(len(seeds))]
    lines+=[' '.join(map(str,seed)) for seed in seeds]
    tables=out/'pdb';back=tables/'b4-backward-pdb-cap12.json';demand=tables/'b4-output-demand-pdb-cap12.json';terminal=tables/'b4-terminal-phase-pdb-cap12.json'
    bm=load(back)
    lines += [f'{len(bm["done_masks"])} 4096 32768',' '.join(map(str,bm['done_masks'])),'16384 32768','8192 32768','1']
    inp=out/'critical-cap12.input';inp.write_text('\n'.join(lines)+'\n')
    labels=out/'closed-labels.bin'
    native=json.loads(call([executable,inp,back.with_suffix('.bin'),demand.with_suffix('.bin'),terminal.with_suffix('.bin'),tables,labels],'native',timeout=130))
    assert native['status']=='EXHAUSTED_FIXED_ORDER' and native['queue']==0
    assert native['states']==native['expanded']==native['closed_label_rows']==1002736
    assert native['generated']==82502307
    assert labels.stat().st_size==24*1002736
    upper=load(P/'controls/known13.json');upper_metrics=verify(graph,upper,478150656)
    assert upper_metrics['peak_bytes']==1703936 and upper_metrics['recompute_cost']==421494784
    call([sys.executable,'-B',P/'check_native.py'],'random-differential')
    call([sys.executable,'-B',P/'native_driver.py','--controls'],'tiny-controls')
    call([sys.executable,'-B',P/'check_drop_falsifier.py'],'drop-falsifier')
    call([sys.executable,'-B',P/'test_generic_region_bounds.py','--repo',ROOT,'--out',out/'generic-region-results.json'],'generic-region-controls')
    call([sys.executable,'-B',P/'check_recursive_actual.py','--repo',ROOT,'--pdb-dir',tables,'--cert-dir',P/'controls/traces'],'recursive-actual-controls')
    call([sys.executable,'-B',P/'native_driver.py','--cap','1572864','--budget','540246016','--states','1000000','--seconds','30','--demand-mode','1','--prefix-from',P/'controls/traces/auxiliary-12u-retimed.json','--pdb',back,'--demand-pdb',demand,'--terminal-pdb',terminal,'--region-bound'],'positive12-control',timeout=45)
    auxiliary12=json.loads(call([sys.executable,'-B',P/'check_auxiliary12.py'],'auxiliary12-exact-budget'))
    receipt=None
    if not args.prepare_only:
        from check_closed import check
        receipt=check(inp,labels,back,demand,terminal,tables)
        (out/'closure-check.json').write_text(json.dumps(receipt,indent=2)+'\n')
        call([sys.executable,'-B',P/'negative_controls.py','--out',out],'proof-negatives')
    work_command=[sys.executable,'-B',P/'work-optimum/replay.py','--out',out/'work-optimum']
    if args.prepare_only:work_command.append('--prepare-only')
    call(work_command,'work-optima',timeout=300)
    work=load(out/'work-optimum/RESULTS.json')
    assert work['status']==('PREPARED_NOT_CLOSURE_CHECKED' if args.prepare_only else 'PASS')
    result=dict(auxiliary12=auxiliary12,work_optima=dict(status=work['status'],
                cases=[{key:c[key] for key in ('cap_units','peak_bytes','minimum_work','strict_excluded_budget','seed_count','dump_sha256')} for c in work['cases']],
                table_audited_edges=work['total_audited_table_edges'],
                result_file=str(out/'work-optimum/RESULTS.json')),
                status='PREPARED_NOT_CLOSURE_CHECKED' if args.prepare_only else 'PASS',evidence='author-checked; separately authored implementation checks within one AI-assisted author team; scientific acceptance pending',
                graph_sha256=GRAPH_SHA,budget=478150656,excluded_peak_bytes=1572864,
                matching_upper_peak_bytes=1703936,upper_recompute_cost=421494784,
                compiler=compiler,flags=flags,python=sys.version,seconds=time.monotonic()-began,native=native,closure=receipt,
                source_sha256=hashlib.sha256((P/'native_search.cpp').read_bytes()).hexdigest(),
                executable_sha256=hashlib.sha256(executable.read_bytes()).hexdigest(),labels_sha256=hashlib.sha256(labels.read_bytes()).hexdigest())
    (out/'replay-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)

if __name__=='__main__':main()
