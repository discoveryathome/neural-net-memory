"""Source-only constructive b4 work curve at auxiliary allocation caps14..82.

Reuses the public allocation/PDB/regional helpers. Every generated point passes
the frozen full verifier; this module alone makes no global optimality claim.
"""
from array import array
import copy
import hashlib
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent;PARENT=HERE.parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(ROOT),str(PARENT),str(PARENT/'allocation')]
from verifier import digest,load,verify
from search import certificate
from pattern_db import PatternDB,INF
from allocation_dp import forward_only,cache_profiles,backward_actions,local_graph
from regional_exact import solve

GRAPH_SHA256='7d60aaf32c25d4d000872f9d317cdb0cbc71c929307eb69faf7e974c795d5854'
ORIGINAL_BUDGETS={22:239075328,36:119537664}

def table_for(tables,requested,unit):
    """Alias only at the proved complete local allocation domain."""
    if type(requested) is not int or requested<10:raise ValueError('unsupported local cap')
    source=min(requested,27);table=tables[source]
    if table.cap!=source*unit:raise ValueError('local table capacity mismatch')
    return table

def load_backward(path,local,cap,unit):
    meta=load(path)
    assert meta['full_graph_sha256']==GRAPH_SHA256
    assert meta['local_graph_sha256']==digest(meta['local_graph'])
    assert meta['local_graph']['nodes']==local['nodes'] and meta['local_graph']['inputs']==local['inputs']
    assert meta['cap_bytes']==cap*unit and meta['row_width']==4096
    assert meta['binary_file']==f'b4-backward-pdb-cap{cap}.bin'
    table=PatternDB(local,cap*unit)
    assert meta['live_nodes']==table.live_nodes and meta['done_masks']==table.done_masks and meta['cost_unit']==table.cost_unit
    raw=path.with_name(meta['binary_file']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==meta['binary_sha256']
    table.dist=array('I');table.dist.frombytes(raw)
    if sys.byteorder!='little':table.dist.byteswap()
    assert len(table.dist)==4096*len(table.done_masks)
    return table

def choices_by_size(tables,owned,peaks):
    choices={}
    for cap,db in tables.items():
        row=db.di[0]*4096;best={}
        for q in range(4096):
            if peaks[q]>cap or db.dist[row+q]==INF:continue
            cost=int(db.dist[row+q])*db.cost_unit;r=owned[q]
            if cost<best.get(r,(10**100,None))[0]:best[r]=(cost,q)
        choices[cap]=best
    return choices

def price(cap,choices,peaks,live_names,full_costs):
    dp={0:(0,[])}
    for block in range(3):
        nxt={}
        for k,(cost,path) in dp.items():
            local_cap=cap-block-k
            if local_cap<10:continue
            for r,(work,q) in choices[min(local_cap,27)].items():
                if cap-3-k-r<10:continue
                offered=cost+work
                if offered<nxt.get(k+r,(10**100,None))[0]:
                    nxt[k+r]=(offered,path+[dict(block=block,mask=q,retained=[x for i,x in enumerate(live_names) if q>>i&1],owned_units=r,local_cap_units=local_cap,forward_only_peak_units=peaks[q],backward_cost=work)])
        dp=nxt
    candidates=[]
    for k,(cost,path) in dp.items():
        local_cap=cap-3-k;source_cap=min(local_cap,22)
        candidates.append(dict(extra_work=cost+full_costs[source_cap],last_work=full_costs[source_cap],last_local_cap_units=local_cap,last_plan_source_cap=source_cap,retained_units=k,earlier=path))
    return dict(min(candidates,key=lambda row:row['extra_work']),cap_units=cap,peak_cap_bytes=cap*131072)

def construct(graph,local,row,tables,full_plans):
    actions=[];live=set();unit=graph['inputs'][0]['bytes'];states=[]
    def add(action,block):
        action=dict(action)
        if 'node' in action:action['node']=action['node'].replace('b0_',f'b{block}_',1)
        actions.append(action)
        if action['op']=='forward':assert action['node'] not in live;live.add(action['node'])
        elif action['op']=='drop':assert action['node'] in live;live.remove(action['node'])
    def cleanup(block):
        for name in sorted(live.copy()):
            if name.startswith(f'b{block}_'):add(dict(op='drop',node=name),block)
    for block,earlier in enumerate(row['earlier']):
        for action in forward_only(local,earlier['retained']):add(action,block)
    for action in full_plans[row['last_plan_source_cap']]['actions']:add(action,3)
    cleanup(3)
    for block in reversed(range(3)):
        add(dict(op='drop',node='b0_residual2'),block)
        earlier=row['earlier'][block];table=table_for(tables,earlier['local_cap_units'],unit)
        assert table.value(earlier['retained'])==earlier['backward_cost']
        plan,count=backward_actions(local,table,earlier['retained']);states.append(count)
        for action in plan:add(action,block)
        cleanup(block)
    c=certificate(graph,actions,row['extra_work'],'pdb-cache-allocation-work-curve',dict(auxiliary_pareto_point=True,not_an_added_original_case=True,global_optimality_claim=False,cap_units=row['cap_units'],
        construction_scope='fixed-entry checkpoint order, all4096 earlier saved-value masks, fixed earlier retention passes, final localcap>=10',
        credit='Doug Colkitt / @Mister-Meeseeks frozen model/verifier/trial; retention-transfer PR6 and PR10 regional search/composition; same-session PDB/allocation work',evidence='author-checked only; scientific acceptance pending'))
    metrics=verify(graph,c,row['extra_work'])
    assert metrics['peak_bytes']==row['peak_cap_bytes'] and metrics['recompute_cost']==row['extra_work']
    return c,dict(tight_edge_states=states,verified_metrics=metrics)

def run(repo,out,shared=None):
    repo=Path(repo).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    began=time.monotonic();deadline=began+120;events=out/'measurements.jsonl'
    def remaining(limit):
        left=deadline-time.monotonic()
        if left<=0:raise RuntimeError('curve construction aggregate limit; incomplete replay')
        return min(limit,left)
    def event(row):
        row=dict(row,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
        with events.open('a') as f:f.write(json.dumps(row,sort_keys=True)+'\n')
    graph=load(repo/'benchmarks/graphs/transformer-b4-t128.json');assert digest(graph)==GRAPH_SHA256
    local=local_graph(graph);unit=graph['inputs'][0]['bytes'];assert unit==131072
    assert sum(v['bytes'] for v in local['nodes']+local['inputs'])==27*unit
    expected=load(HERE/'EXPECTED.json');assert expected['unit_bytes']==unit and expected['graph_sha256']==digest(graph)
    tables={};reused=False
    if shared is not None:
        table_out,audited_result=shared;table_out=Path(table_out)
        assert audited_result['status']=='PASS' and audited_result['graph_sha256']==digest(graph)
        reused=True
    else:table_out=out/'pdb';table_out.mkdir(exist_ok=True)
    for cap in range(10,28):
        if reused:
            path=table_out/f'b4-backward-pdb-cap{cap}.json'
            assert load(path)['binary_sha256']==audited_result['binary_sha256'][path.stem]
            tables[cap]=load_backward(path,local,cap,unit)
        else:
            table=PatternDB(local,cap*unit).build(seconds=remaining(30),states=200000);tables[cap]=table
            table.write(table_out/f'b4-backward-pdb-cap{cap}.json',digest(graph))
        event(dict(kind='backward_table',cap_units=cap,reused=reused))
    owned,peaks=cache_profiles(local,tables[27],unit)
    assert max(owned)==24 and max(peaks)<=27
    choices=choices_by_size(tables,owned,peaks);full_plans={};full_costs={}
    for cap in range(10,23):
        plan=solve(local,cap*unit,10**10,states=500000,seconds=remaining(15));assert plan is not None
        assert verify(local,plan,10**10)['peak_bytes']<=cap*unit
        full_plans[cap]=plan;full_costs[cap]=plan['claims']['recompute_cost']
        event(dict(kind='full_region',cap_units=cap,extra_work=full_costs[cap],states=plan['metadata']['states']))
    assert full_costs[22]==0
    rows=[];sample=None
    for cap,want in expected['rows']:
        row=price(cap,choices,peaks,tables[27].live_nodes,full_costs);assert row['extra_work']==want
        witness,verified=construct(graph,local,row,tables,full_plans)
        assert witness['budget']==want
        path=out/f'cap{cap}.json';path.write_text(json.dumps(witness,indent=2)+'\n')
        result=dict(cap_units=cap,peak_cap_bytes=row['peak_cap_bytes'],extra_work=want,**verified,actions_sha256=digest(witness['actions']),certificate_file=path.name)
        if cap in ORIGINAL_BUDGETS:
            original=copy.deepcopy(witness);original['budget']=ORIGINAL_BUDGETS[cap]
            assert verify(graph,original,ORIGINAL_BUDGETS[cap])==verified['verified_metrics']
            result['original_budget_replay']=ORIGINAL_BUDGETS[cap]
        if cap==22:sample=witness
        if cap==82:assert want==0 and sum(a['op']=='forward' for a in witness['actions'])==56
        rows.append(result);event(dict(kind='verified_curve_point',**result));remaining(120)
    assert [r['cap_units'] for r in rows]==list(range(14,83))
    assert all(b['extra_work']<a['extra_work'] for a,b in zip(rows,rows[1:]))
    negatives=[]
    # These controls challenge graph ownership, physical capacity binding and
    # external-input checkpoint placement, rather than restating the recurrence.
    changed=copy.deepcopy(graph);changed['nodes'][0]['cost']+=1
    try:local_graph(changed)
    except ValueError:negatives.append('changed frozen graph rejected')
    else:raise AssertionError('changed graph accepted')
    forged=dict(tables);forged[24]=tables[27]
    try:table_for(forged,24,unit)
    except ValueError:negatives.append('oversized27u table at24u rejected')
    else:raise AssertionError('invalid local cap alias accepted')
    changed=copy.deepcopy(sample);actions=changed['actions']
    at=next(i for i,a in enumerate(actions) if a==dict(op='drop',node='b0_residual2'));drop=actions.pop(at)
    at=next(i for i,a in enumerate(actions) if a==dict(op='forward',node='b1_norm1'));actions.insert(at,drop)
    try:verify(graph,changed,changed['budget'])
    except ValueError:negatives.append('checkpoint dropped before its reader rejected')
    else:raise AssertionError('early checkpoint drop accepted')
    result=dict(status='PASS',schema='b4-constructive-work-curve/v1',graph_sha256=digest(graph),unit_bytes=unit,rows=rows,negative_controls=negatives,
        reused_audited_back_tables=reused,seconds=time.monotonic()-began,
        scope='all69fullverified auxiliary Pareto upper points; no global work-optimum claim by constructor alone; original22/36budgets also replayed',
        limits=dict(aggregate_seconds=120,backward_table_seconds=30,backward_table_states=200000,full_region_seconds=15,full_region_records=500000,tight_edge_states=200000),
        saturation=dict(cap_units=27,all14owned_plus_immutable_units=27,backward12owned_plus_immutable_units=25),
        evidence='author-checked; same-author-team review and scientific acceptance pending')
    (out/'RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
