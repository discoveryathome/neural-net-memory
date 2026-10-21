"""Exact Pareto frontier of a necessary loss-state dependency-closure relaxation.

This computes a lower bound on every legal schedule, not a schedule or the
minimum temporal peak. See README.md for the mapping from legal action traces.
Only standard-library integers are used; capped searches raise Limited.
"""
import sys
import copy
import math
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from verifier import validate_graph, integer

class Limited(RuntimeError):
    pass

def loss_frontier(g,budget,max_labels=1000000,seconds=60,forced_live=()):
    validate_graph(g)
    forced_live=tuple(forced_live)
    if not integer(budget) or not integer(max_labels,1) or type(seconds) not in (int,float) or not math.isfinite(seconds) or seconds<=0:
        raise ValueError('invalid budget or resource limit')
    ns=g['nodes'];index={n['id']:i for i,n in enumerate(ns)}
    if any(x not in index for x in forced_live):raise ValueError('unknown forced activation')
    needed={x for n in ns for x in n['backward_requires']};outputs=set(g['outputs'])|set(forced_live)
    dep=[sum(1<<index[x] for x in n['deps'] if x in index) for n in ns]
    last=list(range(len(ns)))
    for i,n in enumerate(ns):
        for x in n['deps']:
            if x in index:last[index[x]]=i
    fixed=sum(n['bytes'] for n in g['inputs'])
    labels={0:{fixed:0}};total=1;maximum=1;start=time.monotonic()
    for i,n in enumerate(ns):
        keep=sum(1<<j for j in range(i+1) if last[j]>i)
        next_labels={}
        for covered,pareto in labels.items():
            moves=[(covered|(1<<i),n['bytes'],0)] # retained at loss
            if n['id'] not in outputs:
                if n['id'] not in needed:moves.append((covered,0,0)) # neither
                if n['recomputable'] and covered&dep[i]==dep[i]:moves.append((covered|(1<<i),0,n['cost']))
            for mask,mem,work in moves:
                target=next_labels.setdefault(mask&keep,{})
                for old_mem,old_work in pareto.items():
                    new_mem,new_work=old_mem+mem,old_work+work
                    if new_work>budget:continue
                    if new_work<target.get(new_mem,10**100):
                        if new_mem not in target:
                            total+=1
                            if total>max_labels:raise Limited('label limit; no bound returned')
                        target[new_mem]=new_work
            if time.monotonic()-start>seconds:raise Limited('time limit; no bound returned')
        labels={}
        for mask,pareto in next_labels.items():
            cost=10**100;front={}
            for mem,work in sorted(pareto.items()):
                if work<cost:front[mem]=work;cost=work
            if front:labels[mask]=front
        maximum=max(maximum,sum(len(x) for x in labels.values()))
    assert set(labels)=={0}
    return dict(frontier=sorted(labels[0].items()),labels=total,max_layer_labels=maximum,complete=True,budget_ceiling=budget)

def cut_frontiers(g,budget,max_labels=1000000,seconds=60):
    """Necessary memory/work frontiers at loss and each mandatory first forward.

    Resource limits apply separately to each cut. First-forward cut: every pivot ancestor has been seen; all backwards remain
    pending. All globally backward-required values among those ancestors must
    therefore be retained or regenerated, with output and deps forced resident.
    """
    validate_graph(g)
    result={'loss':loss_frontier(g,budget,max_labels,seconds)}
    needed={x for n in g['nodes'] for x in n['backward_requires']}
    ancestors={x['id']:set() for x in g['inputs']}
    for pivot in g['nodes']:
        name=pivot['id'];seen={name}
        for dep in pivot['deps']:seen|=ancestors[dep]
        ancestors[name]=seen
        sub=copy.deepcopy(g)
        sub['nodes']=[copy.deepcopy(n) for n in g['nodes'] if n['id'] in seen]
        sub['outputs']=[name]
        # Every selected node is an ancestor of pivot, so these requirements
        # validate while representing all pending original-graph backward reads.
        sub['nodes'][-1]['backward_requires']=sorted(needed&seen)
        forced=[x for x in pivot['deps'] if x in seen]
        result['first-forward:'+name]=loss_frontier(sub,budget,max_labels,seconds,forced)
    return result

def lower_bound(frontiers,budget):
    if not integer(budget):raise ValueError('invalid budget')
    if not frontiers or any(not result.get('complete') or not integer(result.get('budget_ceiling')) or budget>result['budget_ceiling'] for result in frontiers.values()):
        raise ValueError('query exceeds a completely enumerated frontier budget')
    by_cut={cut:min(m for m,c in result['frontier'] if c<=budget) for cut,result in frontiers.items()}
    return max(by_cut.values()),sorted(cut for cut,v in by_cut.items() if v==max(by_cut.values()))
