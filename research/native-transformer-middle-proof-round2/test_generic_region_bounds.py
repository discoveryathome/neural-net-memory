"""Unreduced small-graph check of common and nested occupancy lower bounds."""
from functools import lru_cache
import argparse
import heapq
import itertools
import json
import math
from pathlib import Path
import random
import sys
import time

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[2])
parser.add_argument('--out',type=Path,default=Path(__file__).resolve().parent/'generated/generic-region-results.json')
args=parser.parse_args()
sys.path.insert(0,str(args.repo))
from verifier import validate_graph,verify
from search import certificate

def shortest(nodes,fixed,cap,startlive,startdone=0,need_read=False,track=False):
    n=len(nodes);full=(1<<n)-1
    mem=[fixed+sum(v['size'] for i,v in enumerate(nodes) if live>>i&1) for live in range(1<<n)]
    if cap<fixed or mem[startlive]>cap:return math.inf,None,0
    child=[sum(1<<j for j,w in enumerate(nodes) if w['dep']>>i&1) for i in range(n)]
    start=(startlive,startdone,not need_read);best={start:0};queue=[(0,start)];parent={}
    while queue:
        cost,state=heapq.heappop(queue)
        if best[state]!=cost:continue
        live,done,read=state
        if done==full and read:
            if not track:return cost,None,len(best)
            states=[state];actions=[]
            while state!=start:
                previous,action=parent[state];actions.append(action);states.append(previous);state=previous
            return cost,(list(reversed(actions)),list(reversed(states))),len(best)
        moves=[]
        if need_read and not read and live>>(n-1)&1:
            moves.append(((live,done,True),0,('R',n-1)))
        for i,node in enumerate(nodes):
            bit=1<<i
            if live&bit:moves.append(((live^bit,done,read),0,('D',i)))
            elif node['dep']&live==node['dep'] and mem[live|bit]<=cap:
                moves.append(((live|bit,done,read),node['cost'],('F',i)))
            if read and not(done&bit) and child[i]&done==child[i] and node['req']&live==node['req']:
                moves.append(((live,done|bit,read),0,('B',i)))
        for target,extra,action in moves:
            new=cost+extra
            if new<best.get(target,math.inf):
                best[target]=new;parent[target]=(state,action);heapq.heappush(queue,(new,target))
        assert len(best)<=100000
    return math.inf,None,len(best)

def run_case(seed):
    rng=random.Random(seed);blocks=2+seed%2;fixed=rng.randint(1,2);spec=[];anc={'x':{'x'}}
    for block in range(blocks):
        entry='x' if block==0 else f'b{block-1}'
        a,b=f'a{block}',f'b{block}'
        anc[a]={a}|anc[entry];anc[b]={b}|anc[a]|anc[entry]
        for name,deps,req in ((a,[entry],[entry]),(b,[entry,a],rng.sample(sorted(anc[b]),rng.randrange(min(3,len(anc[b]))+1)))):
            spec.append(dict(id=name,deps=deps,bytes=rng.randint(1,3),cost=rng.randint(1,11),backward_cost=1,backward_requires=req,recomputable=True))
    graph=dict(model='activation-memory/v1',id=f'generic-region-{seed}',inputs=[dict(id='x',bytes=fixed)],nodes=spec,outputs=[f'b{blocks-1}'])
    validate_graph(graph)
    idx={v['id']:i for i,v in enumerate(spec)}
    mask=lambda xs:sum(1<<idx[x] for x in xs if x in idx)
    nodes=[dict(size=v['bytes'],cost=v['cost'],dep=mask(v['deps']),req=mask(v['backward_requires'])) for v in spec]
    n=len(nodes);full=(1<<n)-1
    atomic=max(fixed+v['size']+sum(nodes[j]['size'] for j in range(n) if v['dep']>>j&1) for v in nodes)
    reads=max(fixed+sum(nodes[j]['size'] for j in range(n) if v['req']>>j&1) for v in nodes)
    cap=max(atomic,reads)+rng.randrange(4)
    valid=[live for live in range(1<<n) if fixed+sum(v['size'] for i,v in enumerate(nodes) if live>>i&1)<=cap]
    live=rng.choice(valid);undone=rng.randint(1,n);done=full^((1<<undone)-1)
    active=(undone-1)//2
    own=lambda block,bits:sum(nodes[2*block+i]['size'] for i in range(2) if bits>>i&1)
    localnodes=[]
    for block in range(blocks):
        localnodes.append([dict(v,dep=(v['dep']>>(2*block))&3,req=(v['req']>>(2*block))&3) for v in nodes[2*block:2*block+2]])
    local_queries=0
    @lru_cache(None)
    def B(block,c,l,d):
        nonlocal local_queries
        local_queries+=1
        return shortest(localnodes[block],fixed,c,l,d)[0]
    @lru_cache(None)
    def D(block,c,l):
        nonlocal local_queries
        local_queries+=1
        return shortest(localnodes[block],fixed,c,l,0,True)[0]
    @lru_cache(None)
    def E(block,c,m):
        return min(D(block,c,l) for l in range(4) if own(block,l)<=m)
    # Exhaust every valid/invalid local start at every integral cap1..C;
    # these tiny tables are built independently from the global tail.
    for block in range(blocks):
        for c in range(1,cap+1):
            for l in range(4):
                D(block,c,l)
                for d in (0,2,3):B(block,c,l,d)
    local=[(live>>(2*b))&3 for b in range(blocks)]
    initial=[own(b,local[b]) for b in range(active)]
    def components(minima,nested):
        values=[]
        for b in range(active):
            c=cap-sum(minima[:b]) if nested else cap
            values.append(max(D(b,c,local[b]),E(b,c,minima[b])))
        values.append(B(active,cap-sum(minima),local[active],(done>>(2*active))&3))
        return values
    common=nested=math.inf
    for minima in itertools.product(*(range(m+1) for m in initial)):
        common=min(common,sum(components(minima,False)))
        nested=min(nested,sum(components(minima,True)))
    exact,path,count=shortest(nodes,fixed,cap,live,done,track=True)
    assert common<=exact and nested<=exact,(graph,cap,live,done,common,nested,exact)
    owned_checks=0
    if path is not None:
        actions,states=path
        # Build a deliberately unrestricted initialization solely to bind the
        # oracle tail to the unchanged full verifier. Only the tail is capped.
        prefix=[dict(op='forward',node=v['id']) for v in spec]+[dict(op='loss')]
        prefix += [dict(op='backward',node=spec[i]['id']) for i in range(n-1,undone-1,-1)]
        prefix += [dict(op='drop',node=spec[i]['id']) for i in range(n) if not(live>>i&1)]
        ops={'F':'forward','D':'drop','B':'backward'}
        tail=[dict(op=ops[op],node=spec[i]['id']) for op,i in actions]
        certified=certificate(graph,prefix+tail,exact,'generic-region-tail-control')
        verified,history=verify(graph,certified,exact,True)
        assert verified['recompute_cost']==exact
        assert all(t['live_bytes']<=cap for t in history[len(prefix):])
        owned=[sum(nodes[i]['cost'] for op,i in actions if op=='F' and i//2==b) for b in range(blocks)]
        endpoints={i:next(at for at,a in enumerate(actions) if a==('B',2*(i+1))) for i in range(active)}
        for nested_flag in (False,True):
            minima=[]
            for b in range(active):
                end=endpoints[b] if nested_flag else next(at for at,a in enumerate(actions) if a==('B',2*active))
                minima.append(min(own(b,(states[j][0]>>(2*b))&3) for j in range(end+1)))
            values=components(minima,nested_flag)
            for b,value in enumerate(values):
                assert value<=owned[b],(seed,nested_flag,b,value,owned[b],minima,actions,graph)
                owned_checks+=1
    return dict(seed=seed,blocks=blocks,cap=cap,active=active,exact=None if exact==math.inf else exact,common=None if common==math.inf else common,nested=None if nested==math.inf else nested,global_states=count,local_queries=local_queries,actual_owned_component_checks=owned_checks)

started=time.monotonic();cases=[]
for seed in range(240):
    cases.append(run_case(0x2026102100+seed))
    assert time.monotonic()-started<30,'test runtime limit'
result=dict(status='PASS',cases=len(cases),finite_global_cases=sum(c['exact'] is not None for c in cases),unchanged_verifier_tail_controls=len(cases),all_local_caps='1..each global cap, all four live masks and all three backward ideals',actual_owned_component_checks=sum(c['actual_owned_component_checks'] for c in cases),max_global_states=max(c['global_states'] for c in cases),local_queries=sum(c['local_queries'] for c in cases),seconds=time.monotonic()-started,scope='unreduced global all-seen tails and independent exact local Dijkstra; same author-team math stress test',details=cases)
args.out.parent.mkdir(parents=True,exist_ok=True)
args.out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='details'}),flush=True)
