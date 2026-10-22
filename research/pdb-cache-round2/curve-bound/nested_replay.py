"""Add the reviewed nested-endpoint bound to one completed common curve replay."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,random,shutil,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE),str(HERE.parent/'factored-bound'),str(HERE.parent),str(ROOT)]
from verifier import load,digest,verify
from pattern_db import PatternDB
from output_demand_db import OutputDemandDB
from factor_bound import summaries
from pdb_audit import audit_demand
from nested_bound import minimize_nested,enumerate_nested
NEW_BINARY_SHA256={
    'b4-output-demand-pdb-cap9':'806a346fb434ff0df288615680935e3a4aca1d3d64cc674436c413e0157a96ab',
    'b4-output-demand-pdb-cap10':'676dc852e9abf92a460760763df6f4e33551eab7fa769244937ccbd3a39f79bc',
}

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result

def tiny_controls():
    rng=random.Random(2026102201);count=0
    for C in range(9,16):
        for _ in range(4):
            A={};E={};Z={}
            for c in range(9,C+1):
                A[c]=[rng.randrange(500) if r==0 or rng.randrange(4) else None for r in range(4)]
                E[c]=[min(v for v in A[c][:m+1] if v is not None) for m in range(4)]
                Z[c]=[None]*8;best=None
                for s in range(8,C):
                    value=rng.randrange(500);best=value if best is None else min(best,value);Z[c].append(best)
            assert minimize_nested(C,A,E,Z,clip_cap=C)['lower_bound']==enumerate_nested(C,A,E,Z,clip_cap=C)['lower_bound']
            count+=1
    badE={c:list(v) for c,v in E.items()};badE[9][0]+=1
    negativeA={c:list(v) for c,v in A.items()};negativeA[9][0]=-1
    rejected=[]
    for name,args in [('wrong_envelope',(A,badE,Z)),('negative_cost',(negativeA,E,Z)),('missing_capacity',({k:v for k,v in A.items() if k!=9},E,Z)),('missing_terminal',(A,E,{k:v for k,v in Z.items() if k!=9}))]:
        try:minimize_nested(C,*args,clip_cap=C)
        except ValueError:rejected.append(name)
        else:raise AssertionError('Accepted nested input forgery '+name)
    return dict(direct_dp_comparisons=count,rejected_input_forgeries=rejected)

def actual_control(graph,certificate,C,memory,demands,terminal,cost_unit,A,E,Z,lower):
    metrics,trace=verify(graph,certificate,certificate['budget'],True)
    assert metrics['peak_bytes']<=C*131072
    actions=certificate['actions'];index={v['id']:i for i,v in enumerate(graph['nodes'])}
    root=next(i for i,a in enumerate(actions) if a==dict(op='forward',node='b3_gelu'))
    assert trace[root]['recompute_cost']==0
    endpoints=[next(i for i,a in enumerate(actions) if a==dict(op='backward',node=f'b{b+1}_norm1')) for b in range(3)]
    assert root<endpoints[2]<endpoints[1]<endpoints[0]
    local=[]
    for b in range(4):local.append(sum(1<<(index[x]%14) for x in trace[root]['live'] if x in index and index[x]//14==b))
    r=[memory[lv] for lv in local[:3]]
    m=[min(sum(graph['nodes'][index[x]]['bytes']//131072 for x in trace[t]['live'] if x in index and index[x]//14==b) for t in range(root,endpoints[b])) for b in range(3)]
    remaining=[0]*4;seen=set()
    for t,action in enumerate(actions):
        if action['op']=='forward':
            i=index[action['node']]
            if t>root and i in seen:remaining[i//14]+=graph['nodes'][i]['cost']
            seen.add(i)
    components=[];compressed=[];M=0
    for b in range(3):
        cap=min(27,C-M);v=int(demands[cap][local[b]])*cost_unit
        exact=max(v,E[cap][m[b]]);small=max(A[cap][r[b]],E[cap][m[b]])
        assert small<=exact<=remaining[b]
        components.append(exact);compressed.append(small);M+=m[b]
    cap=min(27,C-M);v=int(terminal[cap][local[3]])*cost_unit
    small=Z[cap][min(C-1-sum(r),len(Z[cap])-1)]
    assert small<=v<=remaining[3]
    assert lower<=sum(compressed)+small<=sum(components)+v<=sum(remaining)==metrics['recompute_cost']
    return dict(metrics=metrics,current_r=r,own_endpoint_minima=m,owned_remaining=remaining,identity_sensitive_bounds=components+[v],factored_actual_case=compressed+[small])

def run(repo,out,shared=None):
    """shared=(common_out,common_result) must come from joint_replay.run now."""
    repo=Path(repo).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    common_module=module('nested_common_joint',HERE/'joint_replay.py')
    if shared is None:
        common_out=out/'common';common=common_module.run(repo,common_out)
    else:common_out,common=shared;common_out=Path(common_out).resolve()
    assert json.loads(json.dumps(common))==load(common_out/'RESULTS.json') and common['status']=='PASS'
    lower_module=module('nested_common_lower',HERE/'replay.py');factor=lower_module.factored_module()
    graph=load(repo/'benchmarks/graphs/transformer-b4-t128.json');memory,_=factor.bind_graph(graph)
    frozen=load(HERE.parent/'factored-bound/EXPECTED.json');extra=load(HERE/'EXPECTED.json')
    proof=load(common_out/'factored-tables/RESULTS.json');old_lower=load(common_out/'lower/RESULTS.json')
    assert proof['binary_sha256']==frozen['binary_sha256'] and proof['status']==old_lower['status']=='PASS'
    assert set(proof['table_audits'])==set(frozen['binary_sha256'])
    hashes=dict(proof['binary_sha256']);hashes.update(extra['extra_demand_binary_sha256'])
    terminal={c:lower_module.read_table(common_out/f'factored-tables/b4-terminal-phase-pdb-cap{c}.json',graph,hashes,131072)[1] for c in range(9,16)}
    demands={};audits={};new_hashes={};cost_unit=None
    for cap in range(9,16):
        stem=f'b4-output-demand-pdb-cap{cap}'
        if cap in [9,10]:
            bp=common_out/f'factored-tables/b4-backward-pdb-cap{cap}.json';bm,values=lower_module.read_table(bp,graph,hashes,131072)
            back=PatternDB(bm['local_graph'],cap*131072);assert back.done_masks==bm['done_masks'];back.dist=values
            shutil.copyfile(bp,out/bp.name);shutil.copyfile(bp.parent/bm['binary_file'],out/bm['binary_file'])
            table=OutputDemandDB(bm['local_graph'],cap*131072,back).build(seconds=30)
            path=out/(stem+'.json');meta=table.write(path,bp.name,digest(graph));demands[cap]=table.dist
            assert meta['binary_sha256']==NEW_BINARY_SHA256[stem]
            audits[stem]=audit_demand(path,graph);new_hashes[stem]=meta['binary_sha256']
        else:
            folder='factored-tables' if stem in frozen['binary_sha256'] else 'lower'
            if folder=='lower':assert old_lower['extra_binary_sha256'][stem]==hashes[stem] and stem in old_lower['extra_demand_audits']
            meta,demands[cap]=lower_module.read_table(common_out/f'{folder}/{stem}.json',graph,hashes,131072)
        cost_unit=meta['cost_unit'] if cost_unit is None else cost_unit;assert cost_unit==meta['cost_unit']
    A={};E={};Z={}
    for cap in range(9,16):
        summary=summaries(cap,demands[cap],{cap:terminal[cap]},cost_unit,memory)
        A[cap]=summary['A'];E[cap]=summary['E'];Z[cap]=summary['Z'][cap]
    forced_masks=[live for live in range(4096) if live&3072==3072]
    assert len(forced_masks)==1024 and all(terminal[9][live]==(1<<32)-1 for live in forced_masks)
    wanted={11:524877824,12:463929344,13:405864448,14:354451456,15:312147968};rows=[]
    upper=load(common_out/'constructions/RESULTS.json');upper_by={r['cap_units']:r for r in upper['rows']}
    for cap in range(11,16):
        price=minimize_nested(cap,A,E,Z,clip_cap=15);direct=enumerate_nested(cap,A,E,Z,clip_cap=15)
        assert price['lower_bound']==direct['lower_bound']==wanted[cap]
        row=dict(cap_units=cap,lower_work=price['lower_bound'],factor=price,direct=direct)
        if cap in [14,15]:
            high=upper_by[cap];certificate=load(common_out/'constructions'/high['certificate_file'])
            row['actual_owned_control']=actual_control(graph,certificate,cap,memory,demands,terminal,cost_unit,A,E,Z,price['lower_bound'])
            assert row['actual_owned_control']['metrics']==high['verified_metrics']
            row['extra_work']=high['extra_work'];row['gap']=high['extra_work']-price['lower_bound']
        rows.append(row)
    assert rows[-1]['gap']==0 and rows[-2]['gap']==819200
    forged=lower_module.demand_forgeries(out/'b4-output-demand-pdb-cap10.json',graph)
    result=dict(status='PASS',graph_sha256=digest(graph),rows=rows,exact_caps=list(range(15,83)),exact_points=68,common_exact_caps=common['exact_caps'],open_curve_cap14_gap=819200,universal_peak_floor=dict(peak_units=10,peak_bytes=1310720,cap9_forced_masks_checked=1024,all_terminal_values_unreachable=True),new_binary_sha256=new_hashes,new_table_audits=audits,new_audited_edges=sum(v['edges'] for v in audits.values()),tiny_controls=tiny_controls(),rehashed_table_forgeries=forged,scope='Nested own-output-read endpoint extension closes cap15. Common proof still supplies caps16..82. Cap14 remains open by819200; no new fixed benchmark wins.',evidence='author-checked only; same-author-team review is not independent scientific validation')
    (out/'RESULTS.json').write_text(json.dumps(result,indent=2)+'\n');return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--repo',type=Path,default=ROOT);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    result=run(args.repo,args.out);print(json.dumps(dict(status=result['status'],exact_caps='15..82',open_cap14_gap=result['open_curve_cap14_gap'],new_audited_edges=result['new_audited_edges'])),flush=True)
if __name__=='__main__':main()
