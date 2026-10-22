"""Regenerate and audit all two-block factored work-curve lower bounds."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,sys,tempfile
HERE=Path(__file__).resolve().parent;TEN=HERE.parent/'ten-unit-proof';ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE),str(TEN),str(ROOT)]
from verifier import load,digest,validate_graph
from pattern_db import PatternDB
from output_demand_db import OutputDemandDB
from terminal_phase_db import TerminalPhaseDB
from pdb_audit import audit_backward,audit_demand,audit_terminal
from factor_bound import owned_units,summaries,minimize,enumerate_direct
from controls import tiny_factoring,all_nineteen_roots,actual_components,witness_forgeries

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

def bind_graph(graph):
    validate_graph(graph)
    assert digest(graph)=='49253c00a0941d94630e5323343af6e2d19e7317f26864fc19e01bc782bc638b'
    assert len(graph['inputs'])==1 and graph['inputs'][0]==dict(id='x',bytes=65536)
    assert len(graph['nodes'])==28 and graph['outputs']==['b1_residual2']
    nodes=graph['nodes'][:14];rename={v['id']:v['id'].replace('b0_','b1_',1) for v in nodes};rename['x']='b0_residual2'
    for i,node in enumerate(nodes):
        projected=dict(node,id=rename[node['id']],deps=[rename[x] for x in node['deps']],backward_requires=[rename[x] for x in node['backward_requires']])
        assert projected==graph['nodes'][14+i]
    memory=owned_units(nodes,65536);clip=max(memory)+1
    assert clip==23 and sum(v['bytes'] for v in nodes[:12])//65536+1==21
    assert sum(v['bytes'] for v in nodes[:13])//65536+1+nodes[13]['bytes']//65536==23
    index={v['id']:i for i,v in enumerate(graph['nodes'])};closure=(1<<24)|(1<<25)
    for i in reversed(range(28)):
        if closure>>i&1:closure|=sum(1<<index[x] for x in graph['nodes'][i]['deps'] if x in index)
    assert closure==(1<<26)-1 and sum(graph['nodes'][i]['bytes'] for i in [24,25])==8*65536
    return memory,dict(all14_with_standing_input_units=23,backward12_with_standing_input_units=21,terminal_allocation_maximum_units=23,cut_firsts=26,cut_forced_owned_units=8)

def false_saturation_forgery(out,graph,ten):
    """At23u the all14-live state is valid; a22u alias must be rejected."""
    path=out/'b2-output-demand-pdb-cap23.json';meta=load(path);previous=load(out/'b2-output-demand-pdb-cap22.json')
    with tempfile.TemporaryDirectory(prefix='false-saturation-',dir=out) as tmp:
        folder=Path(tmp);back=load(out/meta['backward_metadata'])
        (folder/meta['backward_metadata']).write_text(json.dumps(back));(folder/back['binary_file']).write_bytes((out/back['binary_file']).read_bytes())
        # Keep the requested cap23 metadata, replace every value by the cap22
        # table, and recompute the checksum. This is a semantic forgery.
        raw=(out/previous['binary_file']).read_bytes();(folder/meta['binary_file']).write_bytes(raw);meta['binary_sha256']=hashlib.sha256(raw).hexdigest()
        changed=folder/path.name;changed.write_text(json.dumps(meta))
        try:audit_demand(changed,graph)
        except (AssertionError,ValueError,KeyError):return dict(change='cap22_values_aliased_as_cap23_rehashed',status='REJECTED')
        raise AssertionError('Accepted false saturation alias')

def run(repo,out):
    repo=Path(repo).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    expected=load(HERE/'EXPECTED.json');graph=load(repo/'benchmarks/graphs/transformer-b2-t64.json');memory,saturation=bind_graph(graph)
    assert expected['graph_sha256']==digest(graph)
    local=dict(graph,id='b2-work-curve-region',nodes=graph['nodes'][:14],outputs=['b0_residual2'])
    terminal={};demand={};hashes={};audits={};cost_unit=None
    for cap in range(9,24):
        back=PatternDB(local,cap*65536).build(seconds=30,states=200000)
        bp=out/f'b2-backward-pdb-cap{cap}.json';bm=back.write(bp,digest(graph))
        table=OutputDemandDB(local,cap*65536,back).build(seconds=30)
        dp=out/f'b2-output-demand-pdb-cap{cap}.json';dm=table.write(dp,bp.name,digest(graph))
        term=TerminalPhaseDB(local,cap*65536,back).build(seconds=30)
        tp=out/f'b2-terminal-phase-pdb-cap{cap}.json';tm=term.write(tp,bp.name,digest(graph))
        for path,meta,audit in [(bp,bm,audit_backward),(dp,dm,audit_demand),(tp,tm,audit_terminal)]:
            assert meta['binary_sha256']==expected['binary_sha256'][path.stem]
            hashes[path.stem]=meta['binary_sha256'];audits[path.stem]=audit(path,graph)
        terminal[cap]=term.dist;demand[cap]=table.dist
        cost_unit=back.cost_unit if cost_unit is None else cost_unit;assert cost_unit==back.cost_unit==dm['cost_unit']==tm['cost_unit']
        print(json.dumps(dict(stage='audited_b2_curve_tables',cap_units=cap)),flush=True)
    assert hashes['b2-backward-pdb-cap21']==hashes['b2-backward-pdb-cap22']==hashes['b2-backward-pdb-cap23']
    rows=[];cache={}
    for cap in range(10,39):
        c=min(cap,23)
        if c not in cache:cache[c]=summaries(demand[c],{t:terminal[t] for t in range(9,c+1)},cost_unit,memory)
        summary=cache[c];price=minimize(cap,summary['A'],summary['E'],summary['Z'],23);direct=enumerate_direct(cap,summary['A'],summary['E'],summary['Z'],23)
        assert price['lower_work']==direct['lower_work']==expected['lower_work'][str(cap)]
        rows.append(dict(cap_units=cap,peak_cap_bytes=cap*65536,lower_work=price['lower_work'],factor=price,direct=direct))
    assert len(rows)==29 and rows[-1]['lower_work']==0 and rows[-2]['lower_work']==81920
    ten=module('b2_curve_tenunit_controls',TEN/'replay.py');negative=ten.negative_tables(out,graph)
    negative.append(false_saturation_forgery(out,graph,ten))
    witness=load(TEN/'positive-witness.json');old_expected=load(TEN/'EXPECTED.json')
    assert hashlib.sha256((TEN/'positive-witness.json').read_bytes()).hexdigest()==old_expected['positive_certificate_file_sha256']
    summary=cache[10]
    actual=actual_components(graph,witness,10,memory,demand[10],terminal,cost_unit,summary,rows[0]['lower_work'])
    nineteen=all_nineteen_roots(graph,memory,demand[10],terminal,cost_unit,rows[0]['lower_work'])
    result=dict(schema='b2-work-curve/v1',status='PASS',graph_sha256=digest(graph),unit_bytes=65536,rows=rows,binary_sha256=hashes,table_audits=audits,total_audited_edges=sum(v['edges'] for v in audits.values()),capacity_saturation=saturation,tiny_factoring=tiny_factoring(),nineteen_roots=nineteen,original_positive_owned_control=actual,negative_tables=negative,negative_witnesses=witness_forgeries(graph,witness),scope='Necessary lower bounds for all29 fixed memory caps10..38. Exactness requires independently reconstructed legal upper witnesses. No new fixed benchmark wins are counted from auxiliary curve points.',evidence='author-checked only; same-author-team review is not independent scientific validation')
    (out/'RESULTS.json').write_text(json.dumps(result,indent=2)+'\n');return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--repo',type=Path,default=ROOT);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    result=run(args.repo,args.out);print(json.dumps(dict(status=result['status'],rows=len(result['rows']),audited_edges=result['total_audited_edges'],negative_tables=len(result['negative_tables']),nineteen_roots=result['nineteen_roots'])),flush=True)
if __name__=='__main__':main()
