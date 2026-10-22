#!/usr/bin/env python3
"""Fixed-cap, minimum-extra-forward-work search for strict chains.

The state records a live tensor mask and a progress coordinate. Before loss the
seen set is a prefix. After loss, eager legal backwards are performed at zero
work and tensors above the remaining backward requirement are dropped: neither
operation can prevent any later useful regeneration in a strict chain.

No symmetry, heuristic eviction, or approximate beam pruning is used.
"""
from __future__ import annotations
import heapq
import math
import time
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from verifier import validate_graph
from search import certificate

class Limited(RuntimeError):
    """Resource exhaustion, never an infeasibility/optimality result."""


def solve(g, cap, budget, *, state_cap=500000, seconds=120):
    validate_graph(g)
    ns=g['nodes']; n=len(ns)
    if n>30: raise ValueError('bounded implementation supports at most 30 nodes')
    if len(g['inputs'])!=1:raise ValueError('requires one immutable input')
    for i,v in enumerate(ns):
        parent=ns[i-1]['id'] if i else g['inputs'][0]['id']
        if v['deps']!=[parent] or v['backward_requires']!=[parent]:
            raise ValueError('requires strict chain and immediate-parent backwards')
    if g['outputs']!=[ns[-1]['id']]:raise ValueError('requires sole terminal output')
    if any(type(x) is not int or x<0 for x in (cap,budget)):
        raise ValueError('invalid nonnegative integer argument')
    if type(state_cap) is not int or state_cap<1:
        raise ValueError('state cap must be a positive integer')
    if (isinstance(seconds,bool) or not isinstance(seconds,(int,float))
            or not math.isfinite(seconds) or seconds<=0):
        raise ValueError('time cap must be positive')
    fixed=sum(v['bytes'] for v in g['inputs'])
    if fixed>cap:return None,dict(status='infeasible',states=0,expanded=0)
    sizes=[v['bytes'] for v in ns]; costs=[v['cost'] for v in ns]
    # Before loss progress m is in [0,n); after loss coordinate n+k+1,
    # where k is the next backward index; k=-1 is the unique goal.
    maskfull=(1<<n)-1
    def encode(live,p):return (p<<n)|live
    def decode(key):return key&maskfull,key>>n
    def normalize(live,k):
        # Return canonical state and the corresponding legal zero-work actions.
        actions=[]
        keep=(1<<k)-1 if k>0 else 0
        for i in range(n-1,-1,-1):
            if live>>i&1 and not(keep>>i&1):
                live^=1<<i;actions.append(dict(op='drop',node=ns[i]['id']))
        while k>=0 and (k==0 or live>>(k-1)&1):
            actions.append(dict(op='backward',node=ns[k]['id']));k-=1
            # The just-used parent and all higher values cannot help an earlier
            # backward or its ancestor-only regeneration.
            keep=(1<<k)-1 if k>0 else 0
            extra=live&~keep
            while extra:
                bit=extra&-extra;i=bit.bit_length()-1
                live^=bit;extra^=bit
                actions.append(dict(op='drop',node=ns[i]['id']))
        return live,n+k+1,actions
    # Memory cache is bounded by encountered masks, not all 2**n masks.
    mem={0:fixed}
    def memory(m):
        got=mem.get(m)
        if got is not None:return got
        orig=m;total=fixed
        while m:
            bit=m&-m;total+=sizes[bit.bit_length()-1];m^=bit
        mem[orig]=total;return total
    # Every absent, previously seen activation that an unfinished backward
    # requires must be regenerated at least once. Ignoring all dependencies
    # gives a valid remaining-work lower bound, before or after loss.
    work_cache={0:0}
    def work(m):
        got=work_cache.get(m)
        if got is not None:return got
        orig=m;total=0
        while m:
            bit=m&-m;total+=costs[bit.bit_length()-1];m^=bit
        work_cache[orig]=total;return total
    start=encode(0,0)
    best={start:0};parents={};queue=[(0,start)]
    expanded=0;started=time.monotonic()
    while queue:
        spent,key=heapq.heappop(queue)
        if spent!=best.get(key):continue
        expanded+=1
        if expanded%1024==0 and time.monotonic()-started>seconds:
            raise Limited(f'time cap {seconds}s; states={len(best)} expanded={expanded}')
        live,p=decode(key)
        if p==n:
            edges=[];at=key
            while at!=start:
                packed=parents[at];prev=packed>>6;op=packed&63
                plive,pp=decode(prev)
                if op>n:
                    edge=[dict(op='drop',node=ns[op-n-1]['id'])]
                else:
                    i=op-1;edge=[dict(op='forward',node=ns[i]['id'])]
                    if pp<n and i==pp and pp+1==n:
                        edge.append(dict(op='loss'))
                        _,_,tail=normalize(plive|(1<<i),n-1);edge.extend(tail)
                    elif pp>=n:
                        _,_,tail=normalize(plive|(1<<i),pp-n-1);edge.extend(tail)
                edges.append(edge);at=prev
            actions=[a for edge in reversed(edges) for a in edge]
            metadata=dict(exact_minimum_work_at_cap=True,cap=cap,
                          states=len(best),expanded=expanded,
                          seconds=time.monotonic()-started,
                          normalization='eager legal backwards and useless suffix drops',
                          domain='strict chain with immediate-parent backward requirements',
                          state_cap=state_cap,time_cap_seconds=seconds)
            c=certificate(g,actions,budget,'chain-exact-fixed-cap',metadata)
            assert c['claims']['recompute_cost']==spent and c['claims']['peak_bytes']<=cap
            return c,dict(status='optimal',minimum_recompute_cost=spent,**metadata)
        before=p<n;m=p if before else n;k=None if before else p-n-1
        maxnode=m if before else k-1
        def relax(target,extra,op):
            new=spent+extra
            if new>budget or new>=best.get(target,10**100):return
            tlive,tp=decode(target)
            required_count=min(tp,n-1) if tp<n else max(0,tp-n-1)
            missing=((1<<required_count)-1)&~tlive
            if new+work(missing)>budget:return
            if target not in best and len(best)>=state_cap:
                raise Limited(f'state cap {state_cap}; expanded={expanded}')
            best[target]=new;parents[target]=(key<<6)|op;heapq.heappush(queue,(new,target))
        # Arbitrary individual drops ensure every retention policy is explored.
        bits=live
        while bits:
            bit=bits&-bits;bits^=bit;i=bit.bit_length()-1
            relax(encode(live^bit,p),0,n+i+1)
        for i in range(min(maxnode,n-1)+1):
            bit=1<<i
            if live&bit or (i and not(live>>(i-1)&1)):continue
            if i<m and not ns[i]['recomputable']:continue
            newlive=live|bit
            if memory(newlive)>cap:continue
            extra=costs[i] if i<m else 0
            newp=p
            if before and i==m:
                newp=m+1
                if newp==n:
                    newlive,newp,_=normalize(newlive,n-1)
            elif not before:
                newlive,newp,_=normalize(newlive,k)
            relax(encode(newlive,newp),extra,i+1)
    return None,dict(status='infeasible_at_budget',cap=cap,budget=budget,
                     states=len(best),expanded=expanded,
                     seconds=time.monotonic()-started,
                     state_cap=state_cap,time_cap_seconds=seconds)
