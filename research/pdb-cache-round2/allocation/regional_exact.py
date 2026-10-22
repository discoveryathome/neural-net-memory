"""Exact minimum recomputation at a fixed cap for small graphs only.

Dijkstra keeps one minimum-cost label per (live,seen,done,loss) state. All
transitions follow activation-memory/v1, including output-before-input-free.
A state/time limit raises Limited and never returns an optimum certificate.

Copied from retention-transfer / PR6 via transformer-regions-round2 / PR10;
only the repository-root lookup changes for this nested package location.
"""
import heapq,time
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from verifier import validate_graph,verify
from search import certificate
class Limited(RuntimeError):pass

def solve(g,cap,budget,states=500000,seconds=60,backward_only=False,initial_live=()):
    validate_graph(g);ns=g['nodes'];n=len(ns)
    if n>16:raise ValueError('small control only, <=16 nodes')
    if any(type(v) is not int or v<0 for v in (cap,budget)):
        raise ValueError('cap and budget must be nonnegative integers')
    idx={v['id']:i for i,v in enumerate(ns)}
    def mask(names):return sum(1<<idx[x] for x in names if x in idx)
    dep=[mask(v['deps']) for v in ns];req=[mask(v['backward_requires']) for v in ns]
    children=[sum(1<<j for j,v in enumerate(ns) if x['id'] in v['deps']) for x in ns]
    fixed=sum(v['bytes'] for v in g['inputs']);mem=[fixed]*(1<<n)
    for m in range(1,1<<n):
        b=m&-m;mem[m]=mem[m^b]+ns[b.bit_length()-1]['bytes']
    full=(1<<n)-1;outputs=mask(g['outputs'])
    if len(set(initial_live))!=len(initial_live) or any(x not in idx for x in initial_live):
        raise ValueError('invalid initial regional activations')
    if initial_live and not backward_only:raise ValueError('initial activations require a backward-only region')
    start=(mask(initial_live),full if backward_only else 0,0,backward_only)
    if mem[start[0]]>cap:return None
    records=[(start,0,None,None)];best={start:0};queue=[(0,0)];expanded=0;t=time.monotonic()
    while queue:
        cost,rid=heapq.heappop(queue);state,_,parent,act=records[rid]
        if cost!=best.get(state):continue
        if time.monotonic()-t>seconds:raise Limited('time limit, no optimum claim')
        live,seen,done,phase=state;expanded+=1
        if phase and done==full:
            acts=[];at=rid
            while records[at][2] is not None:
                acts.append(records[at][3]);at=records[at][2]
            prefix=[]
            if backward_only:
                prefix=[dict(op='forward',node=v['id']) for v in ns]+[dict(op='loss')]
                prefix.extend(dict(op='drop',node=v['id']) for v in ns if v['id'] not in initial_live)
            c=certificate(g,prefix+list(reversed(acts)),budget,'exact-fixed-cap-region',dict(optimal_at_cap=not backward_only,optimal_for_regional_start_state=True,scope='one region with immutable input; supplied start activations' if backward_only else 'one complete training region',initial_live=list(initial_live),cap=cap,states=len(best),expanded=expanded,seconds=time.monotonic()-t,backward_only=backward_only,prefix_actions=len(prefix)))
            metrics,trace=verify(g,c,budget,True)
            tail=max([mem[start[0]]]+[v['live_bytes'] for v in trace[len(prefix):]])
            c['metadata']['tail_peak_bytes']=tail
            assert c['claims']['recompute_cost']==cost and tail<=cap
            return c
        moves=[]
        if not phase and seen==full and live&outputs==outputs:moves.append(((live,seen,done,True),0,dict(op='loss')))
        for i,v in enumerate(ns):
            bit=1<<i
            if live&bit:moves.append(((live^bit,seen,done,phase),0,dict(op='drop',node=v['id'])))
            elif live&dep[i]==dep[i] and (not(seen&bit) or v['recomputable']) and (seen&bit or not phase):
                if mem[live|bit]<=cap:
                    moves.append(((live|bit,seen|bit,done,phase),v['cost'] if seen&bit else 0,dict(op='forward',node=v['id'])))
            if phase and not(done&bit) and done&children[i]==children[i] and live&req[i]==req[i]:
                moves.append(((live,seen,done|bit,phase),0,dict(op='backward',node=v['id'])))
        for target,extra,action in moves:
            new=cost+extra
            if new>budget or new>=best.get(target,10**100):continue
            if len(records)>=states:raise Limited('state limit, no optimum claim')
            nr=len(records);records.append((target,new,rid,action));best[target]=new;heapq.heappush(queue,(new,nr))
    return None
