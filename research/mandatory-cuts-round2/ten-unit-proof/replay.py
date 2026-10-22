"""Regenerate, audit and exhaust the b2 ten-unit necessary-cut relaxation."""
from array import array
from pathlib import Path
import argparse,copy,hashlib,json,subprocess,sys,tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE),str(ROOT)]
from verifier import load,digest,verify,Invalid
from pattern_db import PatternDB
from output_demand_db import OutputDemandDB
from terminal_phase_db import TerminalPhaseDB
from pdb_audit import audit_backward,audit_demand,audit_terminal

def values(path,meta):
    raw=path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==meta['binary_sha256']
    result=array('I');result.frombytes(raw)
    assert result.itemsize==4
    if sys.byteorder!='little':result.byteswap()
    return result

def write_values(path,items):
    items=array('I',items)
    if sys.byteorder!='little':items.byteswap()
    raw=items.tobytes();path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()

def negative_tables(out,graph):
    """Rehash every forgery so rejection tests semantics rather than checksums."""
    stems=dict(backward='b2-backward-pdb-cap10',demand='b2-output-demand-pdb-cap10',terminal='b2-terminal-phase-pdb-cap10')
    cases=[('backward','overclaim_goal'),('backward','underclaim'),
           ('backward','foreign_local_cost'),('demand','foreign_full_hash'),
           ('demand','underclaim'),('demand','wrong_cost_unit'),
           ('terminal','overclaim'),('terminal','phase0_down_live'),
           ('terminal','mismatched_cap')]
    receipts=[]
    with tempfile.TemporaryDirectory(prefix='negative-',dir=out) as temp:
        folder=Path(temp)
        for kind,change in cases:
            for stem in stems.values():
                meta=load(out/(stem+'.json'))
                (folder/(stem+'.json')).write_text(json.dumps(meta))
                (folder/meta['binary_file']).write_bytes((out/meta['binary_file']).read_bytes())
            path=folder/(stems[kind]+'.json');meta=load(path)
            data=values(folder/meta['binary_file'],meta)
            if change=='overclaim_goal':data[meta['done_masks'].index(16383)*4096]=1
            elif change=='underclaim':assert data[0]>0;data[0]-=1
            elif change=='foreign_local_cost':
                meta['local_graph']['nodes'][0]['cost']+=1
                meta['local_graph_sha256']=digest(meta['local_graph'])
            elif change=='foreign_full_hash':meta['full_graph_sha256']='0'*64
            elif change=='wrong_cost_unit':meta['cost_unit']+=1
            elif change=='overclaim':
                at=next(i for i,v in enumerate(data) if 0<v<(1<<32)-1);data[at]+=1
            elif change=='phase0_down_live':data[4096]=0
            elif change=='mismatched_cap':meta['cap_bytes']+=65536
            else:raise AssertionError(change)
            meta['binary_sha256']=write_values(folder/meta['binary_file'],data)
            path.write_text(json.dumps(meta))
            audit={'backward':audit_backward,'demand':audit_demand,'terminal':audit_terminal}[kind]
            try:audit(path,graph)
            except (AssertionError,ValueError,KeyError):receipts.append(dict(table=kind,change=change,status='REJECTED'))
            else:raise AssertionError('Accepted forged '+kind+'/'+change)
    return receipts

def actual_owned_controls(graph,certificate,back,demand,terminal,unit,zero):
    """Compare each local price with actual future work of that same block."""
    metrics,trace=verify(graph,certificate,certificate['budget'],True)
    nodes=graph['nodes'];index={v['id']:i for i,v in enumerate(nodes)}
    remaining=[0,0];seen=set()
    for action in certificate['actions']:
        if action['op']=='forward':
            i=index[action['node']]
            if i in seen:remaining[i//14]+=nodes[i]['cost']
            seen.add(i)
    seen=set();checked=0
    first=next(i for i,a in enumerate(certificate['actions']) if a==dict(op='forward',node='b1_gelu'))
    loss=next(i for i,a in enumerate(certificate['actions']) if a['op']=='loss')
    assert trace[first]['recompute_cost']==0
    for at,action in enumerate(certificate['actions']):
        if action['op']=='forward':
            i=index[action['node']]
            if i in seen:remaining[i//14]-=nodes[i]['cost']
            seen.add(i)
        if at<first or at>loss:continue
        live=sum(1<<index[x] for x in trace[at]['live'] if x in index)
        left=int(demand[live&16383])*unit
        local=(live>>14)&16383
        right=int(back[zero+(local&4095)] if 27 in seen else terminal[int(26 in seen)*8192+(local&8191)])*unit
        assert left<=remaining[0] and right<=remaining[1],(at,left,right,remaining)
        checked+=1
    assert checked==23
    return dict(states=checked,per_block_checks=2*checked,first_gelu_prefix_work=0,metrics=metrics)

def run(repo,out):
    repo=Path(repo).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    expected=load(HERE/'EXPECTED.json')
    graph=load(repo/'benchmarks/graphs/transformer-b2-t64.json')
    assert digest(graph)==expected['graph_sha256']=='49253c00a0941d94630e5323343af6e2d19e7317f26864fc19e01bc782bc638b'
    # The second block uses the same table after renaming its external entry.
    rename={v['id']:v['id'].replace('b0_','b1_',1) for v in graph['nodes'][:14]}
    rename['x']='b0_residual2'
    for i,node in enumerate(graph['nodes'][:14]):
        projected=dict(node,id=rename[node['id']],deps=[rename[x] for x in node['deps']],
                       backward_requires=[rename[x] for x in node['backward_requires']])
        assert projected==graph['nodes'][14+i],'second-block pattern projection mismatch'
    witness_path=HERE/'positive-witness.json'
    assert hashlib.sha256(witness_path.read_bytes()).hexdigest()==expected['positive_certificate_file_sha256']
    witness=load(witness_path);assert digest(witness)==expected['positive_certificate_sha256']
    metrics=verify(graph,witness,110821376)
    assert metrics['peak_bytes']==655360 and metrics['recompute_cost']==106725376
    tighter=copy.deepcopy(witness);tighter['budget']=106725376
    assert verify(graph,tighter,106725376)==metrics
    reuse=load(HERE/'high-budget-reuse.json')
    assert reuse['actions']==witness['actions'] and reuse['budget']==221642752
    assert verify(graph,reuse,221642752)==metrics
    local=dict(graph,id='transformer-b2-t64-local-backward-pattern',nodes=graph['nodes'][:14],outputs=['b0_residual2'])
    back=PatternDB(local,655360).build(seconds=30,states=1000000)
    bp=out/'b2-backward-pdb-cap10.json';bm=back.write(bp,digest(graph))
    demand=OutputDemandDB(local,655360,back).build(seconds=30)
    dp=out/'b2-output-demand-pdb-cap10.json';dm=demand.write(dp,bp.name,digest(graph))
    terminal=TerminalPhaseDB(local,655360,back).build(seconds=30)
    tp=out/'b2-terminal-phase-pdb-cap10.json';tm=terminal.write(tp,bp.name,digest(graph))
    hashes=dict(backward=bm['binary_sha256'],demand=dm['binary_sha256'],terminal=tm['binary_sha256'])
    assert hashes==expected['binary_sha256']
    audits=dict(backward=audit_backward(bp,graph),demand=audit_demand(dp,graph),terminal=audit_terminal(tp,graph))
    forged=negative_tables(out,graph)
    actual=actual_owned_controls(graph,witness,back.dist,demand.dist,terminal.dist,back.cost_unit,back.di[0]*4096)
    witness_negatives=[]
    foreign=copy.deepcopy(graph);foreign['nodes'][0]['cost']+=1
    try:verify(foreign,witness,witness['budget'])
    except Invalid as error:witness_negatives.append(dict(change='foreign_graph_cost',status='REJECTED',reason=str(error)))
    else:raise AssertionError('Accepted foreign graph')
    for kind in ['underclaimed_work','one_below_budget','omitted_regeneration']:
        changed=copy.deepcopy(witness)
        if kind=='underclaimed_work':changed['claims']['recompute_cost']-=1
        elif kind=='one_below_budget':changed['budget']=106725375
        else:
            seen=set()
            for at,action in enumerate(changed['actions']):
                if action['op']!='forward':continue
                if action['node'] in seen:del changed['actions'][at];break
                seen.add(action['node'])
        try:verify(graph,changed,changed['budget'])
        except Invalid as error:witness_negatives.append(dict(change=kind,status='REJECTED',reason=str(error)))
        else:raise AssertionError('Accepted forged witness '+kind)
    results=[]
    for budget,key in [(106725376,'expected_positive'),(106725375,'expected_negative')]:
        proc=subprocess.run([sys.executable,'-B',str(HERE/'micro_preloss.py'),'--repo',str(repo),'--pdb-dir',str(out),'--budget',str(budget)],capture_output=True,text=True,timeout=40)
        assert proc.returncode==0,proc.stderr
        result=json.loads(proc.stdout)
        for field,value in expected[key].items():assert result[field]==value,(field,result[field],value)
        results.append(result)
    answer=dict(status='PASS',graph_sha256=digest(graph),cap_bytes=655360,exact_minimum_additional_work=106725376,positive_metrics=metrics,highest_budget_reuse=dict(budget=221642752,old_work=213614592,new_work=106725376,verified=True,separate_construction=False),binary_sha256=hashes,audits=audits,actual_owned_controls=actual,negative_tables=forged,negative_witnesses=witness_negatives,closures=results,evidence='author-checked only; same-author-team review does not constitute independent scientific validation')
    (out/'RESULTS.json').write_text(json.dumps(answer,indent=2)+'\n')
    return answer

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,default=ROOT);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    print(json.dumps(run(args.repo,args.out),sort_keys=True),flush=True)

if __name__=='__main__':main()
