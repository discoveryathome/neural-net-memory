"""Joint cache allocation for a fixed checkpoint composition of frozen b4.

All regional costs and outside allocations are charged. This constructive
class is not a global minimum-work or smaller-peak result. Doug Colkitt
(@Mister-Meeseeks) supplied the frozen model/verifier; PR6/PR10 supplied the
regional composition, and this package's PatternDB supplies local prices.
"""
from collections import deque
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(ROOT),str(HERE.parent),str(HERE)]
from verifier import digest,load,verify
from search import certificate
from pattern_db import PatternDB,INF
from regional_exact import solve

GRAPH_SHA256='7d60aaf32c25d4d000872f9d317cdb0cbc71c929307eb69faf7e974c795d5854'
EXPECTED={22:234618880,36:117178368}
PRIOR={22:234717184,36:117211136}
BUDGET={22:239075328,36:119537664}

def local_graph(g):
    if digest(g)!=GRAPH_SHA256:raise ValueError('requires unchanged frozen transformer-b4-t128')
    local=copy.deepcopy(g);local['nodes']=local['nodes'][:14]
    local['outputs']=['b0_residual2'];local['id']='b4-allocation-region'
    return local

def forward_only(g,keep=()):
    """PR10 forward-only retention: free firsts, late V, output preserved."""
    nodes={v['id']:v for v in g['nodes']};order=list(nodes)
    for name in list(order):
        if name.endswith('_v'):
            order.remove(name);order.insert(order.index(name[:-1]+'probs')+1,name)
    live=set();actions=[]
    for at,name in enumerate(order):
        actions.append(dict(op='forward',node=name));live.add(name)
        needed=set(g['outputs'])|set(keep)
        for future in order[at+1:]:needed.update(nodes[future]['deps'])
        for old in sorted(live-needed):actions.append(dict(op='drop',node=old));live.remove(old)
    return actions

def cache_profiles(local,db,unit):
    """Price the concrete first pass, including the allocation before drops."""
    names=db.live_nodes;assert len(names)==12
    sizes={v['id']:v['bytes']//unit for v in local['nodes']}
    owned=[0]*4096;peaks=[]
    for q in range(1,4096):
        bit=q&-q;owned[q]=owned[q^bit]+sizes[names[bit.bit_length()-1]]
    for q in range(4096):
        keep={x for i,x in enumerate(names) if q>>i&1}
        live=set();peak=1
        for a in forward_only(local,keep):
            x=a['node']
            if a['op']=='forward':
                assert x not in live and all(y=='x' or y in live for y in local['nodes'][db.idx[x]]['deps'])
                live.add(x);peak=max(peak,1+sum(sizes[y] for y in live))
            else:assert x in live;live.remove(x)
        assert live==keep|{'b0_residual2'}
        peaks.append(peak)
    return owned,peaks

def choose(cap,tables,owned,peaks,full_costs):
    """DP state k is total earlier owned cache units; checkpoints are separate."""
    names=tables[cap].live_nodes;dp={0:(0,[])};layers=[]
    for b in range(3):
        nxt={}
        for k,(cost,path) in dp.items():
            local_cap=cap-b-k
            if local_cap<10:continue
            db=tables[local_cap];offset=db.di[0]*4096
            for q in range(4096):
                r=owned[q]
                if cap-3-k-r<10 or peaks[q]>local_cap:continue
                distance=db.dist[offset+q]
                if distance==INF:continue
                value=cost+int(distance)*db.cost_unit
                if value<nxt.get(k+r,(10**100,None))[0]:
                    nxt[k+r]=(value,path+[dict(block=b,mask=q,retained=[x for i,x in enumerate(names) if q>>i&1],owned_units=r,local_cap_units=local_cap,forward_only_peak_units=peaks[q],backward_cost=int(distance)*db.cost_unit)])
        dp=nxt;layers.append(len(dp))
    candidates=[]
    for k,(cost,path) in dp.items():
        local_cap=cap-3-k;price_cap=min(local_cap,22)
        candidates.append(dict(total_work=cost+full_costs[price_cap],last_local_cap_units=local_cap,last_plan_source_cap=price_cap,last_work=full_costs[price_cap],retained_units=k,earlier=path))
    result=min(candidates,key=lambda row:row['total_work'])
    return dict(result,cap_units=cap,layers=layers)

def price(g,progress=None):
    """Enumerate this fixed class with bounded exact local queries.

    No local cap below10 is used. Caps22+ reuse a checked zero-work full plan.
    A local query limit propagates as failure; no incomplete price is returned.
    """
    local=local_graph(g);unit=g['inputs'][0]['bytes'];tables={};full_costs={}
    deadline=time.monotonic()+120
    def remaining(per_query):
        seconds=deadline-time.monotonic()
        if seconds<=0:raise RuntimeError('aggregate allocation pricing limit; no complete price')
        return min(per_query,seconds)
    for cap in range(10,37):
        db=PatternDB(local,cap*unit).build(seconds=remaining(30),states=200000)
        tables[cap]=db
        if progress:progress(dict(kind='table',cap_units=cap,stats=db.stats))
    owned,peaks=cache_profiles(local,tables[36],unit)
    for cap in range(10,23):
        plan=solve(local,cap*unit,10**10,states=500000,seconds=remaining(15))
        assert plan is not None
        full_costs[cap]=plan['claims']['recompute_cost']
        if progress:progress(dict(kind='full_region',cap_units=cap,cost=full_costs[cap],metadata=plan['metadata']))
    assert full_costs[22]==0
    rows=[choose(cap,tables,owned,peaks,full_costs) for cap in (22,36)]
    remaining(120)
    assert all(row['total_work']==EXPECTED[row['cap_units']] for row in rows)
    return rows,tables

def backward_actions(local,db,keep):
    """A bounded BFS follows tight forward/drop/backward table edges to goal."""
    req=[db.project(v['backward_requires']) for v in local['nodes']]
    children=[sum(1<<j for j,v in enumerate(local['nodes']) if a['id'] in v['deps']) for a in local['nodes']]
    live=db.project(keep);start=(live,0);full=(1<<14)-1
    queue=deque([start]);parents={start:None};value0=db.dist[db.di[0]*4096+live]
    assert value0!=INF
    while queue:
        live,done=state=queue.popleft()
        if done==full:
            actions=[]
            while parents[state] is not None:
                state,action=parents[state];actions.append(action)
            return list(reversed(actions)),len(parents)
        value=db.dist[db.di[done]*4096+live];moves=[]
        for i,name in enumerate(db.live_nodes):
            bit=1<<i
            if live&bit:moves.append(((live^bit,done),0,dict(op='drop',node=name)))
            elif live&db.deps[i]==db.deps[i] and db.valid[live|bit]:
                moves.append(((live|bit,done),db.costs[i],dict(op='forward',node=name)))
        for i,v in enumerate(local['nodes']):
            bit=1<<i
            if not done&bit and done&children[i]==children[i] and live&req[i]==req[i]:
                moves.append(((live,done|bit),0,dict(op='backward',node=v['id'])))
        for target,cost,action in moves:
            if target in parents:continue
            newlive,newdone=target;distance=db.dist[db.di[newdone]*4096+newlive]
            if distance!=INF and cost+distance==value:
                parents[target]=(state,action);queue.append(target)
                if len(parents)>200000:raise RuntimeError('tight-edge reconstruction limit')
    raise RuntimeError('no tight completion; no construction')

def construct(g,row,tables):
    local=local_graph(g);actions=[];live=set();C=row['cap_units']
    def add(action,b):
        a=dict(action)
        if 'node' in a:a['node']=a['node'].replace('b0_',f'b{b}_',1)
        actions.append(a)
        if a['op']=='forward':assert a['node'] not in live;live.add(a['node'])
        elif a['op']=='drop':assert a['node'] in live;live.remove(a['node'])
    def cleanup(b):
        for name in sorted(live.copy()):
            if name.startswith(f'b{b}_'):add(dict(op='drop',node=name),b)
    for b,earlier in enumerate(row['earlier']):
        for a in forward_only(local,earlier['retained']):add(a,b)
    assert row['last_plan_source_cap']==15
    full=load(HERE/'controls/full-block-cap15.json')
    rebound=dict(full,graph_id=local['id'],graph_sha256=digest(local))
    assert verify(local,rebound,full['budget'])['recompute_cost']==row['last_work']
    for a in full['actions']:add(a,3)
    cleanup(3)
    for b in reversed(range(3)):
        add(dict(op='drop',node='b0_residual2'),b)
        earlier=row['earlier'][b];db=tables[earlier['local_cap_units']]
        plan,_=backward_actions(local,db,earlier['retained'])
        for a in plan:add(a,b)
        cleanup(b)
    c=certificate(g,actions,BUDGET[C],'cache-allocation-dp-round2')
    assert c['claims']['peak_bytes']==C*g['inputs'][0]['bytes']
    assert c['claims']['recompute_cost']==row['total_work']==EXPECTED[C]<PRIOR[C]
    return c

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,default=HERE/'generated');args=p.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True);began=time.monotonic()
    log=out/'measurements.jsonl'
    def event(x):
        x=dict(x,utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        with log.open('a') as f:f.write(json.dumps(x,sort_keys=True)+'\n')
    graph=load(ROOT/'benchmarks/graphs/transformer-b4-t128.json')
    rows,tables=price(graph,event);metrics=[]
    for row in rows:
        C=row['cap_units'];saved=load(HERE/f'certificates/transformer-b4-t128-cap{C}.json')
        actual=verify(graph,saved,BUDGET[C]);rebuilt=construct(graph,row,tables)
        assert rebuilt['actions']==saved['actions'] and rebuilt['claims']==actual
        metrics.append(dict(cap_units=C,claims=actual,prior_work=PRIOR[C],saved_work=PRIOR[C]-actual['recompute_cost']))
    result=dict(status='PASS',scope='constructive fixed-entry checkpoint allocation; no global minimum-work claim',graph_sha256=GRAPH_SHA256,
                rows=rows,metrics=metrics,seconds=time.monotonic()-began,action_traces_reconstructed=True)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)

if __name__=='__main__':main()
