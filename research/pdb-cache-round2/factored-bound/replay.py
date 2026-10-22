"""Source-only replay of the two exact factored fixed-peak work bounds."""
from array import array
from pathlib import Path
import argparse,copy,hashlib,json,sys,tempfile
HERE=Path(__file__).resolve().parent;PARENT=HERE.parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE),str(PARENT),str(ROOT)]
from verifier import load,digest,verify,validate_graph
from pattern_db import PatternDB
from output_demand_db import OutputDemandDB
from terminal_phase_db import TerminalPhaseDB
from pdb_audit import audit_backward,audit_demand,audit_terminal
from factor_bound import owned_units,summaries,minimize
from direct_enumeration import enumerate_price
from controls import tiny_factoring,all_9178_roots,actual_components,witness_forgeries

def bind_graph(graph):
    validate_graph(graph)
    assert digest(graph)=='7d60aaf32c25d4d000872f9d317cdb0cbc71c929307eb69faf7e974c795d5854'
    assert len(graph['inputs'])==1 and graph['inputs'][0]['id']=='x'
    unit=graph['inputs'][0]['bytes'];assert unit==131072 and len(graph['nodes'])==56
    local=graph['nodes'][:14]
    for block in range(4):
        remap={v['id']:v['id'].replace('b0_',f'b{block}_',1) for v in local}
        remap['x']='x' if block==0 else f'b{block-1}_residual2'
        for i,node in enumerate(local):
            wanted=dict(node,id=remap[node['id']],deps=[remap[d] for d in node['deps']],backward_requires=[remap[d] for d in node['backward_requires']])
            assert wanted==graph['nodes'][14*block+i]
    memory=owned_units(local,unit)
    assert max(memory)+1==27 and sum(v['bytes'] for v in local[:12])//unit+1==25
    assert sum(v['bytes'] for v in local[:13])//unit+1+local[13]['bytes']//unit==27
    index={v['id']:i for i,v in enumerate(graph['nodes'])}
    deps=[sum(1<<index[d] for d in v['deps'] if d in index) for v in graph['nodes']]
    forced=(1<<52)|(1<<53);closure=forced
    for i in reversed(range(56)):
        if closure>>i&1:closure|=deps[i]
    assert closure==(1<<54)-1 and sum(graph['nodes'][i]['bytes'] for i in [52,53])//unit==8
    return memory,dict(full_local14_maximum_units=27,backward_local12_maximum_units=25,terminal_output_allocation_maximum_units=27,cut_firsts=54)

def read_values(path,meta):
    raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==meta['binary_sha256']
    values=array('I');values.frombytes(raw);assert values.itemsize==4
    if sys.byteorder!='little':values.byteswap()
    return values

def write_values(path,values):
    values=array('I',values)
    if sys.byteorder!='little':values.byteswap()
    raw=values.tobytes();path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()

def table_forgeries(out,graph):
    stems=dict(backward='b4-backward-pdb-cap22',demand='b4-output-demand-pdb-cap22',terminal='b4-terminal-phase-pdb-cap22')
    cases=[('backward','overclaim_goal'),('backward','underclaim'),('backward','foreign_local_cost'),('backward','wrong_done_masks'),('demand','foreign_full_hash'),('demand','underclaim'),('demand','wrong_cost_unit'),('demand','foreign_input'),('terminal','overclaim'),('terminal','phase0_down_live'),('terminal','wrong_phase_metadata'),('terminal','mismatched_cap')]
    receipts=[]
    with tempfile.TemporaryDirectory(prefix='factored-negative-',dir=out) as tmp:
        folder=Path(tmp)
        for kind,change in cases:
            for stem in stems.values():
                meta=load(out/(stem+'.json'));(folder/(stem+'.json')).write_text(json.dumps(meta));(folder/meta['binary_file']).write_bytes((out/meta['binary_file']).read_bytes())
            path=folder/(stems[kind]+'.json');meta=load(path);values=read_values(folder/meta['binary_file'],meta)
            if change=='overclaim_goal':values[meta['done_masks'].index(16383)*4096]=1
            elif change=='underclaim':assert values[0]>0;values[0]-=1
            elif change=='foreign_local_cost':meta['local_graph']['nodes'][0]['cost']+=1;meta['local_graph_sha256']=digest(meta['local_graph'])
            elif change=='wrong_done_masks':meta['done_masks'][0]=1
            elif change=='foreign_full_hash':meta['full_graph_sha256']='0'*64
            elif change=='wrong_cost_unit':meta['cost_unit']+=1
            elif change=='foreign_input':meta['local_graph']['inputs'][0]['bytes']+=131072;meta['local_graph_sha256']=digest(meta['local_graph'])
            elif change=='overclaim':at=next(i for i,v in enumerate(values) if 0<v<(1<<32)-1);values[at]+=1
            elif change=='phase0_down_live':values[4096]=0
            elif change=='wrong_phase_metadata':meta['phases'][0]['down_seen']=True
            elif change=='mismatched_cap':meta['cap_bytes']+=131072
            else:raise AssertionError(change)
            meta['binary_sha256']=write_values(folder/meta['binary_file'],values);path.write_text(json.dumps(meta))
            audit={'backward':audit_backward,'demand':audit_demand,'terminal':audit_terminal}[kind]
            try:audit(path,graph)
            except (AssertionError,ValueError,KeyError):receipts.append(dict(table=kind,change=change,status='REJECTED'))
            else:raise AssertionError('Accepted semantic forgery '+kind+'/'+change)
    return receipts

def run(repo,out):
    repo=Path(repo).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    expected=load(HERE/'EXPECTED.json');graph=load(repo/'benchmarks/graphs/transformer-b4-t128.json');memory,saturation=bind_graph(graph)
    assert expected['graph_sha256']==digest(graph)
    local=dict(graph,id='b4-factored-bound-region',nodes=graph['nodes'][:14],outputs=['b0_residual2']);unit=graph['inputs'][0]['bytes']
    terminal={};demand={};table_audits={};binary_hashes={};cost_unit=None
    for cap in range(9,28):
        back=PatternDB(local,cap*unit).build(seconds=30,states=1000000)
        bp=out/f'b4-backward-pdb-cap{cap}.json';bm=back.write(bp,digest(graph))
        assert bm['binary_sha256']==expected['binary_sha256'][bp.stem]
        term=TerminalPhaseDB(local,cap*unit,back).build(seconds=30)
        tp=out/f'b4-terminal-phase-pdb-cap{cap}.json';tm=term.write(tp,bp.name,digest(graph))
        assert tm['binary_sha256']==expected['binary_sha256'][tp.stem]
        cost_unit=back.cost_unit if cost_unit is None else cost_unit;assert cost_unit==back.cost_unit==tm['cost_unit']
        terminal[cap]=term.dist
        table_audits[bp.stem]=audit_backward(bp,graph);table_audits[tp.stem]=audit_terminal(tp,graph)
        binary_hashes[bp.stem]=bm['binary_sha256'];binary_hashes[tp.stem]=tm['binary_sha256']
        if cap in [12,13,22,27]:
            table=OutputDemandDB(local,cap*unit,back).build(seconds=30)
            dp=out/f'b4-output-demand-pdb-cap{cap}.json';dm=table.write(dp,bp.name,digest(graph))
            assert dm['binary_sha256']==expected['binary_sha256'][dp.stem]
            demand[cap]=table.dist;table_audits[dp.stem]=audit_demand(dp,graph);binary_hashes[dp.stem]=dm['binary_sha256']
        print(json.dumps(dict(stage='audited_local_tables',cap_units=cap)),flush=True)
    # The complete mask/edge allocation domain is already present by27u.
    # Every cap comparison in all3 local problems is therefore identical above27u.
    assert binary_hashes['b4-backward-pdb-cap25']==binary_hashes['b4-backward-pdb-cap26']==binary_hashes['b4-backward-pdb-cap27']
    tiny=tiny_factoring();rows=[]
    for cap in [12,13,22,36]:
        summary=summaries(cap,demand[min(cap,27)],{c:terminal[c] for c in range(9,min(cap,27)+1)},cost_unit,memory)
        price=minimize(summary['A'],summary['E'],summary['Z'],cap,27)
        assert price['lower_bound']==expected['bounds'][str(cap)]
        aliases={c:summary['Z'][min(c,27)] for c in range(9,cap+1)}
        direct=enumerate_price(cap,summary['A'],summary['E'],aliases)
        assert direct['minimum']==price['lower_bound']
        row=dict(cap_units=cap,peak_cap_bytes=cap*unit,lower_work=price['lower_bound'],factor=price,direct_enumeration=direct,A=summary['A'],E=summary['E'])
        if cap==12:row['all_9178_roots']=all_9178_roots(graph,memory,demand[12],terminal,cost_unit,price['lower_bound'])
        elif cap==13:row['diagnostic_upper_work']=421494784;row['diagnostic_gap']=421494784-price['lower_bound'];row['work_optimality_claim']=False
        else:
            path=HERE/f'positive-cap{cap}.json';assert hashlib.sha256(path.read_bytes()).hexdigest()==expected['certificate_sha256'][str(cap)]
            witness=load(path);actual=actual_components(graph,witness,cap,memory,demand[min(cap,27)],terminal,cost_unit,summary,price)
            assert actual['metrics']['recompute_cost']==price['lower_bound']
            tighter=copy.deepcopy(witness);tighter['budget']=price['lower_bound'];assert verify(graph,tighter,tighter['budget'])==actual['metrics']
            row['actual_owned_control']=actual;row['negative_witnesses']=witness_forgeries(graph,witness)
        rows.append(row)
    forged=table_forgeries(out,graph)
    result=dict(status='PASS',graph_sha256=digest(graph),capacity_saturation=saturation,rows=rows,binary_sha256=binary_hashes,table_audits=table_audits,total_audited_edges=sum(v['edges'] for v in table_audits.values()),tiny_factoring=tiny,negative_table_forgeries=forged,evidence='author-checked only; same-author-team reviews are not independent scientific validation')
    (out/'RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--repo',type=Path,default=ROOT);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    result=run(args.repo,args.out)
    print(json.dumps(dict(status=result['status'],edges=result['total_audited_edges'],table_forgeries=len(result['negative_table_forgeries']),tiny=result['tiny_factoring'],rows=[dict(cap_units=r['cap_units'],lower_work=r['lower_work'],direct_configurations=r['direct_enumeration']['direct_six_coordinate_configurations']) for r in result['rows']]),sort_keys=True),flush=True)

if __name__=='__main__':main()
