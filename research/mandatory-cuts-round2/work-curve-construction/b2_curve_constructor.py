"""Full verified auxiliary b2 work curve; no standalone optimality claim.

PDB generation and exact regional search come from this parent package. The
retention profiles and tight-edge reconstruction adapt the same author team's
b4 allocation follow-up, copied here without a dependency on that proposal.
"""
from array import array
from collections import deque
import copy,hashlib,json,sys,time
from pathlib import Path

HERE=Path(__file__).resolve().parent;PARENT=HERE.parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(ROOT),str(PARENT),str(PARENT/'ten-unit-proof')]
from verifier import digest,load,verify
from search import certificate
from regional_exact import solve
from compose_schedule import forward_only
from pattern_db import PatternDB,INF

GRAPH_SHA256='49253c00a0941d94630e5323343af6e2d19e7317f26864fc19e01bc782bc638b'
ORIGINAL_BUDGETS={10:[110821376,221642752],13:[55410688],19:[27705344]}

def local_graph(graph):
    if digest(graph)!=GRAPH_SHA256:raise ValueError('requires unchanged frozen transformer-b2-t64')
    local=copy.deepcopy(graph);local['nodes']=local['nodes'][:14]
    local['outputs']=['b0_residual2'];local['id']='b2-curve-region'
    return local

def table_for(tables,requested,unit):
    if type(requested) is not int or requested<9:raise ValueError('unsupported local capacity')
    source=min(requested,23);table=tables[source]
    if table.cap!=source*unit:raise ValueError('local table capacity mismatch')
    return table

def load_backward(path,local,cap,unit):
    meta=load(path);assert meta['full_graph_sha256']==GRAPH_SHA256
    assert meta['local_graph_sha256']==digest(meta['local_graph'])
    assert meta['local_graph']['nodes']==local['nodes'] and meta['local_graph']['inputs']==local['inputs']
    assert meta['cap_bytes']==cap*unit and meta['row_width']==4096
    assert meta['binary_file']==f'b2-backward-pdb-cap{cap}.bin'
    table=PatternDB(local,cap*unit)
    assert meta['live_nodes']==table.live_nodes and meta['done_masks']==table.done_masks and meta['cost_unit']==table.cost_unit
    raw=path.with_name(meta['binary_file']).read_bytes();assert hashlib.sha256(raw).hexdigest()==meta['binary_sha256']
    table.dist=array('I');table.dist.frombytes(raw)
    if sys.byteorder!='little':table.dist.byteswap()
    assert len(table.dist)==4096*len(table.done_masks)
    return table

def profiles(local,db,unit):
    names=db.live_nodes;assert len(names)==12
    sizes={v['id']:v['bytes']//unit for v in local['nodes']};owned=[0]*4096;peaks=[]
    for q in range(1,4096):
        b=q&-q;owned[q]=owned[q^b]+sizes[names[b.bit_length()-1]]
    for q in range(4096):
        keep={x for i,x in enumerate(names) if q>>i&1};live=set();peak=1
        for a in forward_only(local,keep):
            name=a['node']
            if a['op']=='forward':
                assert name not in live and all(x=='x' or x in live for x in local['nodes'][db.idx[name]]['deps'])
                live.add(name);peak=max(peak,1+sum(sizes[x] for x in live))
            else:assert name in live;live.remove(name)
        assert live==keep|{'b0_residual2'};peaks.append(peak)
    return owned,peaks

def backward_actions(local,db,keep):
    req=[db.project(v['backward_requires']) for v in local['nodes']]
    child=[sum(1<<j for j,v in enumerate(local['nodes']) if n['id'] in v['deps']) for n in local['nodes']]
    start=(db.project(keep),0);queue=deque([start]);parent={start:None};full=16383
    assert db.value(keep) is not None
    while queue:
        live,done=state=queue.popleft()
        if done==full:
            actions=[]
            while parent[state] is not None:state,a=parent[state];actions.append(a)
            return list(reversed(actions)),len(parent)
        value=db.dist[db.di[done]*4096+live];moves=[]
        for i,name in enumerate(db.live_nodes):
            bit=1<<i
            if live&bit:moves.append(((live^bit,done),0,dict(op='drop',node=name)))
            elif live&db.deps[i]==db.deps[i] and db.valid[live|bit]:moves.append(((live|bit,done),db.costs[i],dict(op='forward',node=name)))
        for i,node in enumerate(local['nodes']):
            bit=1<<i
            if not done&bit and done&child[i]==child[i] and live&req[i]==req[i]:moves.append(((live,done|bit),0,dict(op='backward',node=node['id'])))
        for target,extra,action in moves:
            if target in parent:continue
            other=db.dist[db.di[target[1]]*4096+target[0]]
            if other!=INF and extra+other==value:
                parent[target]=(state,action);queue.append(target)
                if len(parent)>200000:raise RuntimeError('tight-edge reconstruction limit')
    raise RuntimeError('no tight completion; no witness')

def price(cap,tables,owned,peaks,full_costs,unit):
    table=table_for(tables,cap,unit);offset=table.di[0]*4096;candidates=[]
    for q in range(4096):
        r=owned[q];last=cap-1-r
        if last<9 or peaks[q]>cap or table.dist[offset+q]==INF:continue
        source=min(last,20);work=int(table.dist[offset+q])*table.cost_unit
        candidates.append(dict(extra_work=work+full_costs[source],backward_work=work,owned_units=r,retained=[x for i,x in enumerate(table.live_nodes) if q>>i&1],mask=q,last_local_cap_units=last,last_plan_source_cap=source,last_work=full_costs[source]))
    return dict(min(candidates,key=lambda r:r['extra_work']),cap_units=cap,peak_cap_bytes=cap*unit)

def construct(graph,local,row,tables,full_plans):
    actions=[];live=set();unit=graph['inputs'][0]['bytes']
    def add(action,block):
        action=dict(action)
        if 'node' in action:action['node']=action['node'].replace('b0_',f'b{block}_',1)
        actions.append(action)
        if action['op']=='forward':assert action['node'] not in live;live.add(action['node'])
        elif action['op']=='drop':assert action['node'] in live;live.remove(action['node'])
    def cleanup(block):
        for name in sorted(live.copy()):
            if name.startswith(f'b{block}_'):add(dict(op='drop',node=name),block)
    for action in forward_only(local,row['retained']):add(action,0)
    for action in full_plans[row['last_plan_source_cap']]['actions']:add(action,1)
    cleanup(1);add(dict(op='drop',node='b0_residual2'),0)
    table=table_for(tables,row['cap_units'],unit);assert table.value(row['retained'])==row['backward_work']
    plan,count=backward_actions(local,table,row['retained'])
    for action in plan:add(action,0)
    cleanup(0)
    witness=certificate(graph,actions,row['extra_work'],'two-block-allocation-work-curve',dict(auxiliary_pareto_point=True,not_an_added_original_case=True,global_optimality_claim=False,cap_units=row['cap_units'],
        scope='one entry checkpoint and all4096 useful cache masks; final local cap>=9',
        credit='Doug Colkitt / @Mister-Meeseeks frozen model/verifier/trial; PR6/PR10 regional composition; parent ten-unit PDB proof; same-author-team allocation follow-up',evidence='author-checked only; scientific acceptance pending'))
    metrics=verify(graph,witness,row['extra_work'])
    assert metrics['peak_bytes']==row['peak_cap_bytes'] and metrics['recompute_cost']==row['extra_work']
    return witness,dict(tight_edge_states=count,verified_metrics=metrics)

def run(repo,out,shared=None):
    repo=Path(repo).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    began=time.monotonic();deadline=began+120
    def remaining(limit):
        left=deadline-time.monotonic()
        if left<=0:raise RuntimeError('aggregate curve limit; incomplete replay')
        return min(limit,left)
    def event(row):
        row=dict(row,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
        with (out/'measurements.jsonl').open('a') as f:f.write(json.dumps(row,sort_keys=True)+'\n')
    graph=load(repo/'benchmarks/graphs/transformer-b2-t64.json');local=local_graph(graph);unit=graph['inputs'][0]['bytes'];assert unit==65536
    assert len(graph['nodes'])==28 and sum(v['bytes'] for v in local['nodes']+local['inputs'])==23*unit
    expected=load(HERE/'EXPECTED.json');assert expected['graph_sha256']==digest(graph) and expected['unit_bytes']==unit
    tables={};reused=shared is not None
    if reused:
        table_out,audited=shared;table_out=Path(table_out)
        assert audited['status']=='PASS' and audited['graph_sha256']==digest(graph)
    else:table_out=out/'pdb';table_out.mkdir(exist_ok=True)
    for cap in range(9,24):
        path=table_out/f'b2-backward-pdb-cap{cap}.json'
        if reused:
            assert load(path)['binary_sha256']==audited['binary_sha256'][path.stem]
            tables[cap]=load_backward(path,local,cap,unit)
        else:
            table=PatternDB(local,cap*unit).build(seconds=remaining(30),states=200000);tables[cap]=table;table.write(path,digest(graph))
        event(dict(kind='backward_table',cap_units=cap,reused=reused))
    owned,peaks=profiles(local,tables[23],unit);assert max(owned)==20 and max(peaks)<=23 and max(tables[23].memory)==21*unit
    full_plans={};full_costs={}
    for cap in range(9,21):
        plan=solve(local,cap*unit,10**10,states=500000,seconds=remaining(15));assert plan is not None
        assert verify(local,plan,10**10)['peak_bytes']<=cap*unit
        full_plans[cap]=plan;full_costs[cap]=plan['claims']['recompute_cost'];event(dict(kind='full_region',cap_units=cap,work=full_costs[cap],states=plan['metadata']['states']))
    assert full_costs[20]==0
    rows=[];sample=None
    for cap,want in expected['rows']:
        row=price(cap,tables,owned,peaks,full_costs,unit);assert row['extra_work']==want
        witness,verified=construct(graph,local,row,tables,full_plans);path=out/f'cap{cap}.json';path.write_text(json.dumps(witness,indent=2)+'\n')
        result=dict(cap_units=cap,peak_cap_bytes=row['peak_cap_bytes'],extra_work=want,**verified,actions_sha256=digest(witness['actions']),certificate_file=path.name)
        if cap in ORIGINAL_BUDGETS:
            for budget in ORIGINAL_BUDGETS[cap]:
                original=copy.deepcopy(witness);original['budget']=budget;assert verify(graph,original,budget)==verified['verified_metrics']
            result['original_budget_replays']=ORIGINAL_BUDGETS[cap]
        if cap==19:sample=witness
        if cap==38:assert want==0 and sum(a['op']=='forward' for a in witness['actions'])==28
        rows.append(result);event(dict(kind='verified_curve_point',**result));remaining(120)
    assert [r['cap_units'] for r in rows]==list(range(10,39)) and all(b['extra_work']<a['extra_work'] for a,b in zip(rows,rows[1:]))
    negatives=[];changed=copy.deepcopy(graph);changed['nodes'][0]['cost']+=1
    try:local_graph(changed)
    except ValueError:negatives.append('changed frozen graph rejected')
    else:raise AssertionError('changed graph accepted')
    forged=dict(tables);forged[20]=tables[23]
    try:table_for(forged,20,unit)
    except ValueError:negatives.append('oversized23u table at20u rejected')
    else:raise AssertionError('invalid alias accepted')
    changed=copy.deepcopy(sample);actions=changed['actions'];at=next(i for i,a in enumerate(actions) if a==dict(op='drop',node='b0_residual2'));drop=actions.pop(at)
    at=next(i for i,a in enumerate(actions) if a==dict(op='forward',node='b1_norm1'));actions.insert(at,drop)
    try:verify(graph,changed,changed['budget'])
    except ValueError:negatives.append('checkpoint dropped before reader rejected')
    else:raise AssertionError('early checkpoint drop accepted')
    result=dict(status='PASS',schema='b2-constructive-work-curve/v1',graph_sha256=digest(graph),unit_bytes=unit,rows=rows,negative_controls=negatives,reused_audited_back_tables=reused,seconds=time.monotonic()-began,
        saturation=dict(full_local_units=23,backward_local_units=21,full_training_zero_units=20),
        limits=dict(aggregate_seconds=120,backward_states=200000,backward_seconds=30,full_records=500000,full_seconds=15,tight_states=200000),
        scope='all29full auxiliary Pareto upper points; original four budgets also replayed; no standalone global optimality claim',evidence='author-checked; same-author-team review and scientific acceptance pending')
    (out/'RESULTS.json').write_text(json.dumps(result,indent=2)+'\n');return result
