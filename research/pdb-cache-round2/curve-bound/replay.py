"""Necessary lower-work curve; the parent joins verified constructive rows."""
from array import array
from pathlib import Path
import argparse,copy,hashlib,importlib.util,json,shutil,sys,tempfile
HERE=Path(__file__).resolve().parent;PARENT=HERE.parent;FACTOR=PARENT/'factored-bound';ROOT=HERE.parents[2]
sys.path[:0]=[str(FACTOR),str(PARENT),str(ROOT)]
from verifier import load,digest
from pattern_db import PatternDB
from output_demand_db import OutputDemandDB
from factor_bound import summaries,minimize
from pdb_audit import audit_demand

def factored_module():
    spec=importlib.util.spec_from_file_location('shared_factored_bound_replay',FACTOR/'replay.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def read_table(path,graph,hashes,unit):
    meta=load(path)
    assert meta['full_graph_sha256']==digest(graph)
    assert meta['local_graph']['nodes']==graph['nodes'][:14] and meta['local_graph']['inputs']==graph['inputs'] and meta['local_graph']['outputs']==['b0_residual2']
    assert digest(meta['local_graph'])==meta['local_graph_sha256']
    cap=int(path.stem.rsplit('cap',1)[1]);assert meta['cap_bytes']==cap*unit
    raw=(path.parent/meta['binary_file']).read_bytes();actual=hashlib.sha256(raw).hexdigest()
    assert actual==meta['binary_sha256']==hashes[path.stem]
    values=array('I');values.frombytes(raw);assert values.itemsize==4
    if sys.byteorder!='little':values.byteswap()
    if '-backward-' in path.stem:
        assert meta['row_width']==4096 and meta['live_nodes']==[v['id'] for v in graph['nodes'][:12]]
        assert len(values)==len(meta['done_masks'])*4096
    elif '-terminal-phase-' in path.stem:
        assert meta['row_width']==8192 and meta['live_nodes']==[v['id'] for v in graph['nodes'][:13]]
        assert len(values)==16384 and meta['phases']==[dict(down_seen=False,output_seen=False),dict(down_seen=True,output_seen=False)]
    else:
        assert meta['row_width']==16384 and meta['live_nodes']==[v['id'] for v in graph['nodes'][:14]] and len(values)==16384
    return meta,values

def demand_forgeries(path,graph):
    """Extra capacity-family rejection controls, rehashed before audit."""
    original=load(path);source=path.parent;back=load(source/original['backward_metadata']);receipts=[]
    with tempfile.TemporaryDirectory(prefix='curve-negative-',dir=source) as tmp:
        folder=Path(tmp)
        for change in ['overclaim','underclaim','wrong_local_size','wrong_cap']:
            (folder/original['backward_metadata']).write_text(json.dumps(back));(folder/back['binary_file']).write_bytes((source/back['binary_file']).read_bytes())
            meta=copy.deepcopy(original);values=array('I');values.frombytes((source/original['binary_file']).read_bytes())
            if sys.byteorder!='little':values.byteswap()
            if change=='overclaim':values[0]+=1
            elif change=='underclaim':assert values[0]>0;values[0]-=1
            elif change=='wrong_local_size':meta['local_graph']['nodes'][0]['bytes']+=131072;meta['local_graph_sha256']=digest(meta['local_graph'])
            elif change=='wrong_cap':meta['cap_bytes']+=131072
            if sys.byteorder!='little':values.byteswap()
            raw=values.tobytes();(folder/meta['binary_file']).write_bytes(raw);meta['binary_sha256']=hashlib.sha256(raw).hexdigest();forged=folder/path.name;forged.write_text(json.dumps(meta))
            try:audit_demand(forged,graph)
            except (AssertionError,ValueError,KeyError):receipts.append(dict(change=change,status='REJECTED'))
            else:raise AssertionError('Accepted extra demand-table forgery '+change)
    return receipts

def run(repo,out,shared=None):
    """shared must be (table_out,result) from factored-bound.run in this replay."""
    repo=Path(repo).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    expected=load(HERE/'EXPECTED.json');assert hashlib.sha256((FACTOR/'EXPECTED.json').read_bytes()).hexdigest()==expected['factored_expected_sha256']
    factor=factored_module()
    if shared is None:
        table_out=out/'factored-tables';proof=factor.run(repo,table_out)
    else:table_out,proof=shared;table_out=Path(table_out).resolve()
    proof=json.loads(json.dumps(proof))
    assert proof==load(table_out/'RESULTS.json') and proof['status']=='PASS'
    frozen=load(FACTOR/'EXPECTED.json');assert proof['binary_sha256']==frozen['binary_sha256']
    assert set(proof['table_audits'])==set(frozen['binary_sha256'])
    graph=load(repo/'benchmarks/graphs/transformer-b4-t128.json');memory,saturation=factor.bind_graph(graph);unit=expected['unit_bytes']
    assert digest(graph)==expected['graph_sha256']==proof['graph_sha256']
    hashes=dict(frozen['binary_sha256']);hashes.update(expected['extra_demand_binary_sha256'])
    terminal={c:read_table(table_out/f'b4-terminal-phase-pdb-cap{c}.json',graph,hashes,unit)[1] for c in range(9,28)}
    demand={};audits={};extra_hashes={};cost_unit=None
    capacities=[11,13]+list(range(14,28))
    for cap in capacities:
        stem=f'b4-output-demand-pdb-cap{cap}'
        if stem in frozen['binary_sha256']:dm,demand[cap]=read_table(table_out/(stem+'.json'),graph,hashes,unit)
        else:
            bp=table_out/f'b4-backward-pdb-cap{cap}.json';bm,values=read_table(bp,graph,hashes,unit)
            back=PatternDB(bm['local_graph'],cap*unit)
            assert back.done_masks==bm['done_masks'] and back.cost_unit==bm['cost_unit'];back.dist=values
            shutil.copyfile(bp,out/bp.name);shutil.copyfile(bp.parent/bm['binary_file'],out/bm['binary_file'])
            table=OutputDemandDB(bm['local_graph'],cap*unit,back).build(seconds=30)
            dp=out/(stem+'.json');dm=table.write(dp,bp.name,digest(graph));demand[cap]=table.dist
            assert dm['binary_sha256']==hashes[stem]
            audits[stem]=audit_demand(dp,graph);extra_hashes[stem]=dm['binary_sha256']
        cost_unit=dm['cost_unit'] if cost_unit is None else cost_unit;assert cost_unit==dm['cost_unit']
    summary_cache={};rows=[];diagnostics=[]
    wanted={r['cap_units']:r for r in expected['rows']+expected['diagnostics']}
    for cap in [11,13]+list(range(14,83)):
        c=min(cap,27)
        if c not in summary_cache:summary_cache[c]=summaries(cap,demand[c],{k:terminal[k] for k in range(9,c+1)},cost_unit,memory)
        summary=summary_cache[c];price=minimize(summary['A'],summary['E'],summary['Z'],cap,27)
        assert price['lower_bound']==wanted[cap]['lower_work']
        row=dict(cap_units=cap,peak_cap_bytes=cap*unit,lower_work=price['lower_bound'],argmin=price['argmin'],dp_states=price['states_by_stage'],dp_transitions=price['transitions'])
        (diagnostics if cap in [11,13] else rows).append(row)
    assert len(rows)==69 and all(rows[i]['lower_work']>=rows[i+1]['lower_work'] for i in range(68)) and rows[-1]['lower_work']==0
    forged=demand_forgeries(out/'b4-output-demand-pdb-cap14.json',graph)
    result=dict(schema='b4-work-curve/v1',status='PASS',graph_sha256=digest(graph),unit_bytes=unit,rows=rows,diagnostics=diagnostics,extra_demand_audits=audits,extra_audited_edges=sum(v['edges'] for v in audits.values()),extra_binary_sha256=extra_hashes,negative_controls=forged,shared_factored_audit_edges=proof['total_audited_edges'],capacity_saturation=saturation,scope='Necessary work lower bounds; exactness requires separately reconstructed and full-verifier-checked upper witnesses. Non-suite points are not additional fixed benchmark wins.',evidence='author-checked only')
    (out/'RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--repo',type=Path,default=ROOT);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    result=run(args.repo,args.out)
    print(json.dumps(dict(status=result['status'],rows=len(result['rows']),extra_audited_edges=result['extra_audited_edges'],negative_controls=len(result['negative_controls']),scope=result['scope']),sort_keys=True),flush=True)

if __name__=='__main__':main()
