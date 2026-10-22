"""Regenerate the C13 work exclusion; verify all tables, labels and upper trace.

Only dependencies are this repository's unchanged verifier/search helper and
the already included parent PDB generators/auditors and normalization controls.
No installed solver, saved binary, external PR checkout, or network is used.
"""
import argparse,copy,hashlib,itertools,json,os,shutil,struct,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;PARENT=HERE.parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(ROOT),str(PARENT/'pdb'),str(HERE)]
from verifier import load,digest,validate_graph,verify
from search import certificate
from pattern_db import PatternDB
from output_demand_db import OutputDemandDB
from terminal_phase_db import TerminalPhaseDB
import replay_pdb,replay_terminal
replay_pdb.load=load;replay_pdb.digest=digest;replay_pdb.validate_graph=validate_graph
replay_terminal.R=ROOT;replay_terminal.load=load;replay_terminal.digest=digest

def seeds(graph,cap=13):
    ns=graph['nodes'];index={v['id']:i for i,v in enumerate(ns)}
    forced=(1<<index['b3_up'])|(1<<index['b3_gelu'])
    closure={index['b3_gelu']};todo=list(closure)
    while todo:
        for x in ns[todo.pop()]['deps']:
            if x in index and index[x] not in closure:closure.add(index[x]);todo.append(index[x])
    assert closure==set(range(54))
    small=[i for i in range(54) if not(forced>>i&1) and ns[i]['bytes']==131072]
    big=[i for i in range(54) if not(forced>>i&1) and ns[i]['bytes']==4*131072]
    assert len(small)==38 and len(big)==14
    assert cap in (13,14)
    result=[forced|sum(1<<i for i in chosen) for count in range(cap-8) for chosen in itertools.combinations(small,count)]
    for large in big:
        for count in range(cap-12):
            result.extend(forced|(1<<large)|sum(1<<i for i in chosen) for chosen in itertools.combinations(small,count))
    assert len(result)==len(set(result))=={13:83007,14:585481}[cap]
    return result

def input_text(graph,live_seeds,back,*,cap=13,budget=421494783,demand=0):
    ns=graph['nodes'];names=[v['id'] for v in ns];index={x:i for i,x in enumerate(names)}
    mask=lambda xs:sum(1<<index[x] for x in set(xs) if x in index)
    upper=load(HERE/('positive-witness.json' if cap==13 else 'positive-cap14.json'));order=[]
    for action in upper['actions']:
        if action['op']=='forward' and index[action['node']] not in order:order.append(index[action['node']])
    assert len(order)==56 and set(order[:54])==set(range(54)) and order[54:]==[54,55]
    lines=[f'56 1 {cap} {budget} 1000000 30 20 {demand}']
    for v in ns:
        child=mask(w['id'] for w in ns if v['id'] in w['deps'])
        lines.append(f'{v["id"]} {v["bytes"]//131072} {v["cost"]} {mask(v["deps"])} {mask(v["backward_requires"])} {child} {int(v["recomputable"])}')
    lines+=[' '.join(map(str,order)),str(mask(graph['outputs'])),str(len(live_seeds))]
    lines += [f'{live} 0 54 0' for live in live_seeds]
    lines += [f'{len(back["done_masks"])} 4096 32768',' '.join(map(str,back['done_masks'])),'16384 32768','8192 32768','1']
    return '\n'.join(lines)+'\n'

def reconstruct_positive(graph,upper,native):
    names=[v['id'] for v in graph['nodes']];index={x:i for i,x in enumerate(names)};nodes={v['id']:v for v in graph['nodes']}
    _,trace=verify(graph,upper,upper['budget'],True)
    root=next(i for i,a in enumerate(upper['actions']) if a==dict(op='forward',node='b3_gelu'))
    actions=copy.deepcopy(upper['actions'][:root+1]);live=set(trace[root]['live'])-{'x'};seen={a['node'] for a in actions if a['op']=='forward'};done=set();sealed=False
    children={x:{v['id'] for v in graph['nodes'] if x in v['deps']} for x in names}
    required={x:set(v['backward_requires'])&set(names) for x,v in nodes.items()}
    def emit(op,x=None):
        nonlocal sealed
        actions.append(dict(op=op,**({} if x is None else dict(node=x))))
        if op=='forward':live.add(x);seen.add(x)
        elif op=='drop':live.remove(x)
        elif op=='backward':done.add(x)
        elif op=='loss':sealed=True
    def close():
        if not sealed and len(seen)==56 and set(graph['outputs'])<=live:emit('loss')
        if sealed:
            for x in reversed(names):
                if x not in done and children[x]<=done and required[x]<=live:emit('backward',x)
            useful=set().union(*(required[x] for x in names if x not in done));todo=list(useful)
            while todo:
                for d in nodes[todo.pop()]['deps']:
                    if d in nodes and d not in useful:useful.add(d);todo.append(d)
            for x in names:
                if x in live and x not in useful:emit('drop',x)
    close()
    for i,gone in native['steps']:
        for j,x in enumerate(names):
            if gone>>j&1:emit('drop',x)
        emit('forward',names[i]);close()
    witness=certificate(graph,actions,upper['budget'],'nested-bound-positive-native-control')
    actual=verify(graph,witness,upper['budget']);want=verify(graph,upper,upper['budget'])
    assert actual['peak_bytes']<=want['peak_bytes'] and actual['recompute_cost']==native['cost']==want['recompute_cost']
    return witness,actual

def run(out,prepare_only=False):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True);tmp=out/'tmp';tmp.mkdir(exist_ok=True)
    began=time.monotonic();expected=load(HERE/'EXPECTED.json');graph=load(ROOT/'benchmarks/graphs/transformer-b4-t128.json');validate_graph(graph)
    assert digest(graph)==expected['graph_sha256'] and graph['inputs']==[dict(id='x',bytes=131072)]
    assert hashlib.sha256((HERE/'native_search.cpp').read_bytes()).hexdigest()==expected['native_source_sha256']
    assert all(v['recomputable'] and v['bytes'] in (131072,524288) for v in graph['nodes'])
    for b in range(4):
        remap={v['id']:v['id'].replace('b0_',f'b{b}_',1) for v in graph['nodes'][:14]};remap['x']='x' if b==0 else f'b{b-1}_residual2'
        for i,v in enumerate(graph['nodes'][:14]):assert dict(v,id=remap[v['id']],deps=[remap[x] for x in v['deps']],backward_requires=[remap[x] for x in v['backward_requires']])==graph['nodes'][14*b+i]
    env=dict(os.environ,TMPDIR=str(tmp),CLANG_MODULE_CACHE_PATH=str(tmp),NATIVE_PROOF_OUT=str(out))
    def call(command,name,timeout=120):
        proc=subprocess.run(list(map(str,command)),cwd=ROOT,env=env,capture_output=True,text=True,timeout=timeout)
        (out/(name+'.log')).write_text(proc.stdout+proc.stderr)
        if proc.returncode:raise RuntimeError((name,proc.returncode,proc.stdout,proc.stderr))
        return proc.stdout
    direct=Path('/Library/Developer/CommandLineTools/usr/bin/clang++');compiler=str(direct) if direct.exists() else shutil.which('c++')
    if compiler is None:raise RuntimeError('C++17 compiler unavailable; proof source preserved')
    flags=['-std=c++17','-O2'];sdk=Path('/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk')
    if sys.platform=='darwin' and sdk.exists():flags=['-isysroot',str(sdk)]+flags
    executable=out/'native_search';call([compiler,*flags,HERE/'native_search.cpp','-o',executable],'compile',60)
    tables=out/'pdb';tables.mkdir(exist_ok=True);local=dict(graph,id='transformer-b4-t128-local-backward-pattern',nodes=graph['nodes'][:14],outputs=['b0_residual2']);audits={};hashes={}
    for c in range(9,15):
        back=PatternDB(local,c*131072).build(seconds=15,states=200000);bp=tables/f'b4-backward-pdb-cap{c}.json';bm=back.write(bp,digest(graph))
        demand=OutputDemandDB(local,c*131072,back).build(seconds=15);dp=tables/f'b4-output-demand-pdb-cap{c}.json';dm=demand.write(dp,bp.name,digest(graph))
        terminal=TerminalPhaseDB(local,c*131072,back).build(seconds=15);tp=tables/f'b4-terminal-phase-pdb-cap{c}.json';tm=terminal.write(tp,bp.name,digest(graph))
        for p,meta,audit in [(bp,bm,lambda p:replay_pdb.audit_backward(p,graph)),(dp,dm,lambda p:replay_pdb.audit_demand(p,graph)),(tp,tm,replay_terminal.audit)]:
            assert meta['binary_file']==p.stem+'.bin' and meta['cost_unit']==32768 and meta['cap_bytes']==c*131072
            assert meta['binary_sha256']==expected['table_binary_sha256'][p.stem]
            hashes[p.stem]=meta['binary_sha256'];audits[p.stem]=audit(p)
        print(json.dumps(dict(stage='audited_tables',cap=c)),flush=True)
    assert hashes==expected['table_binary_sha256']
    table_negatives=dict(backward=replay_pdb.negative_controls(bp,graph,False),demand=replay_pdb.negative_controls(dp,graph,True),terminal=replay_terminal.negative_controls(tp))
    call([sys.executable,'-B',PARENT/'check_native.py'],'unreduced-normalization-controls')
    call([sys.executable,'-B',PARENT/'test_generic_region_bounds.py','--repo',ROOT,'--out',out/'generic-nested-controls.json'],'generic-nested-controls')
    cases=[]
    for cap in (13,14):
        want=expected['cases'][str(cap)];case=out/f'cap{cap}';case.mkdir(exist_ok=True);minimum=want['minimum_work']
        upper=load(HERE/want['positive_file']);assert hashlib.sha256((HERE/want['positive_file']).read_bytes()).hexdigest()==want['positive_file_sha256']
        positive=verify(graph,upper,want['original_budget']);assert positive['peak_bytes']==cap*131072 and positive['recompute_cost']==minimum
        tight=copy.deepcopy(upper);tight['budget']=minimum;assert verify(graph,tight,minimum)==positive
        original_negative=[]
        for kind in ['underclaim','one_below','omitted_repeated_forward']:
            forged=copy.deepcopy(tight)
            if kind=='underclaim':forged['claims']['recompute_cost']-=1
            elif kind=='one_below':forged['budget']-=1
            else:
                seen=set()
                for i,a in enumerate(forged['actions']):
                    if a['op']=='forward':
                        if a['node'] in seen:del forged['actions'][i];break
                        seen.add(a['node'])
            try:verify(graph,forged,forged['budget'])
            except ValueError:original_negative.append(kind)
            else:raise AssertionError('accepted forged upper trace '+kind)
        backmeta=load(tables/f'b4-backward-pdb-cap{cap}.json');allseeds=seeds(graph,cap)
        inp=case/f'critical-cap{cap}.input';inp.write_text(input_text(graph,allseeds,backmeta,cap=cap,budget=want['strict_budget']))
        labels=case/'closed-labels.bin';base=[executable,inp,tables/f'b4-backward-pdb-cap{cap}.bin',tables/f'b4-output-demand-pdb-cap{cap}.bin',tables/f'b4-terminal-phase-pdb-cap{cap}.bin',tables]
        native=json.loads(call([*base,labels],f'cap{cap}-native',40))
        for key,value in want['native'].items():assert native[key]==value,(cap,key,native[key],value)
        assert labels.stat().st_size==24*native['closed_label_rows']
        _,history=verify(graph,upper,upper['budget'],True);root=next(i for i,a in enumerate(upper['actions']) if a==dict(op='forward',node='b3_gelu'));index={v['id']:i for i,v in enumerate(graph['nodes'])};live=sum(1<<index[x] for x in history[root]['live'] if x in index)
        pos=case/'positive-critical.input';pos.write_text(input_text(graph,[live],backmeta,cap=cap,budget=minimum,demand=1));base[1]=pos
        generated=json.loads(call(base,f'cap{cap}-positive-native',40));assert generated['status']=='FEASIBLE' and generated['cost']==minimum
        witness,constructed=reconstruct_positive(graph,upper,generated);(case/'positive-reconstructed.json').write_text(json.dumps(witness,indent=2)+'\n')
        call([sys.executable,'-B',HERE/'actual_controls.py','--repo',ROOT,'--tables',tables,'--native',executable,'--out',case/'actual-controls','--cap',cap],f'cap{cap}-actual-controls')
        closure=None;proof_negatives=None
        if not prepare_only:
            from check_closed import check
            closure=check(ROOT,inp,labels,tables);(case/'closure.json').write_text(json.dumps(closure,indent=2)+'\n')
            call([sys.executable,'-B',HERE/'negative_controls.py','--repo',ROOT,'--out',case,'--tables',tables,'--cap',cap],f'cap{cap}-closed-proof-forgeries')
            proof_negatives=load(case/'proof-negatives.json')
        cases.append(dict(cap_units=cap,minimum_work=minimum,peak_bytes=cap*131072,strict_excluded_budget=want['strict_budget'],original_budget=want['original_budget'],original_positive_metrics=positive,positive_reconstructed_metrics=constructed,seed_count=len(allseeds),native={k:v for k,v in native.items() if k not in ['initial_h_values','layers']},closure=closure,upper_forgeries=original_negative,proof_forgeries=proof_negatives,dump_sha256=hashlib.sha256(labels.read_bytes()).hexdigest()))
        print(json.dumps(dict(stage='case_completed',cap=cap,closure_checked=closure is not None)),flush=True)
    result=dict(status='PREPARED_NOT_CLOSURE_CHECKED' if prepare_only else 'PASS',graph_sha256=digest(graph),cases=cases,
        table_binary_sha256=hashes,table_audits=audits,total_audited_table_edges=sum(x['edges'] for x in audits.values()),table_forgeries=table_negatives,
        native_source_sha256=hashlib.sha256((HERE/'native_search.cpp').read_bytes()).hexdigest(),compiler=compiler,flags=flags,seconds=time.monotonic()-began,
        limits=dict(native_records=1000000,native_seconds=30,table_states=200000,table_seconds=15),scope='Necessary-cut-domain exclusions plus explicit normalization mapping and matching whole verified witnesses prove fixed-cap work minima at13u/14u; these auxiliary work optima add no original fixed benchmark peak wins',evidence='Codex generated and author-checked; same-author-team reviews are not independent scientific validation')
    (out/'RESULTS.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--prepare-only',action='store_true');args=parser.parse_args()
    result=run(args.out,args.prepare_only);print(json.dumps(dict(status=result['status'],native_states=[x['native']['states'] for x in result['cases']],audited_table_edges=result['total_audited_table_edges'],minimum_work=[x['minimum_work'] for x in result['cases']])),flush=True)
