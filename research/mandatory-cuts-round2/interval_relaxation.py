"""Ordered mandatory-event relaxation; feasible solutions are not schedules.

Old-node transfers and dependency-closed interval regeneration are charged once
per disjoint interval. Newly included guaranteed-seen nodes may have been prefetched
before a preceding cut; old deps are forced only when first execution after that cut
is guaranteed by descent from its first-forward pivot.
"""
import argparse
import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from verifier import load, validate_graph, verify
from ortools.sat.python import cp_model
import ortools


def events(graph, pivots, qk_backward_cut=False):
    validate_graph(graph)
    ns = graph['nodes'];idx={v['id']:i for i,v in enumerate(ns)}
    def mask(names):return sum(1<<idx[x] for x in names if x in idx)
    ancestor=[]
    for i,v in enumerate(ns):
        a=1<<i
        for d in v['deps']:
            if d in idx:a|=ancestor[idx[d]]
        ancestor.append(a)
    if len(set(pivots))!=len(pivots) or not pivots or any(p not in idx for p in pivots):
        raise ValueError('distinct known pivots required')
    for p,q in zip(pivots,pivots[1:]):
        if not ancestor[idx[q]]&(1<<idx[p]):raise ValueError('pivots must form ancestor spine')
    full=(1<<len(ns))-1
    out=[]
    for p in pivots:
        v=ns[idx[p]]
        out.append(dict(kind='forward',node=p,seen=ancestor[idx[p]],forced=(1<<idx[p])|mask(v['deps'])))
    out.append(dict(kind='loss',seen=full,forced=mask(graph['outputs'])))
    for p in reversed(pivots):
        out.append(dict(kind='backward',node=p,seen=full,forced=mask(ns[idx[p]]['backward_requires'])))
        if qk_backward_cut and p.endswith('_scores'):
            prefix=p[:-len('scores')];q,k=prefix+'q',prefix+'k'
            if q not in idx or k not in idx or not {q,k}<=set(ns[idx[p]]['deps']):
                raise ValueError('q/k backward group requires both score consumers')
            earlier=pivots[pivots.index(p)-1] if pivots.index(p)>0 else None
            if earlier is None or any(not anc_i&(1<<idx[earlier]) for anc_i in (ancestor[idx[q]],ancestor[idx[k]])):
                raise ValueError('q/k group must precede earlier selected backward by ancestry')
            shared=set(ns[idx[q]]['backward_requires'])&set(ns[idx[k]]['backward_requires'])
            out.append(dict(kind='backward_any',nodes=[q,k],seen=full,forced=mask(shared)))
    return out,ancestor


def mapping(graph, cuts, cert):
    metrics,trace=verify(graph,cert,cert['budget'],True)
    idx={v['id']:i for i,v in enumerate(graph['nodes'])}
    first={};back={};loss=None;seen=set();repeated=[]
    for at,a in enumerate(cert['actions']):
        op=a['op'];name=a.get('node')
        if op=='forward':
            if name in seen:repeated.append((at,idx[name]))
            else:first[name]=at;seen.add(name)
        elif op=='backward':back[name]=at
        elif op=='loss':loss=at
    positions=[first[e['node']] if e['kind']=='forward' else back[e['node']] if e['kind']=='backward' else min(back[n] for n in e['nodes']) if e['kind']=='backward_any' else loss for e in cuts]
    if any(p is None for p in positions) or positions!=sorted(set(positions)):
        raise ValueError('actual witness does not meet guaranteed event order')
    live=[]
    for event,at in zip(cuts,positions):
        live.append(sum(1<<idx[v] for v in trace[at]['live'] if v in idx)&event['seen'])
    regen=[]
    for t in range(len(cuts)-1):
        r=0
        for at,i in repeated:
            if positions[t]<at<=positions[t+1] and cuts[t]['seen']&(1<<i):r|=1<<i
        regen.append(r)
    return dict(live=live,regen=regen,positions=positions,actual_recompute_cost=metrics['recompute_cost'])


def build(graph, pivots, cap, budget=None, *, naive=False, hint=None,qk_backward_cut=False,persistent_allocations=False):
    cuts,anc=events(graph,pivots,qk_backward_cut);ns=graph['nodes'];n=len(ns)
    if any(type(v) is not int or v<0 for v in (cap,)) or (budget is not None and (type(budget) is not int or budget<0)):
        raise ValueError('nonnegative integer cap/budget required')
    idx={v['id']:i for i,v in enumerate(ns)}
    fixed=sum(v['bytes'] for v in graph['inputs'])
    unit=math.gcd(fixed,*(v['bytes'] for v in ns));costunit=math.gcd(*(v['cost'] for v in ns))
    m=cp_model.CpModel()
    live=[];regen=[];costs=[]
    for t,e in enumerate(cuts):
        row={i:m.new_bool_var(f'L{t}_{i}') for i in range(n) if e['seen']&(1<<i)}
        live.append(row)
        m.add(fixed//unit+sum(ns[i]['bytes']//unit*v for i,v in row.items())<=cap//unit)
        for i,v in row.items():
            if e['forced']&(1<<i):m.add(v==1)
    for t,(a,b) in enumerate(zip(cuts,cuts[1:])):
        row={i:m.new_bool_var(f'R{t}_{i}') for i in range(n) if a['seen']&(1<<i)}
        regen.append(row)
        persistent={}
        if persistent_allocations:
            for i,r in row.items():
                pv=m.new_bool_var(f'P{t}_{i}');persistent[i]=pv
                m.add(pv<=live[t][i]);m.add(pv<=live[t+1][i]);m.add(pv+r<=1)
                m.add(pv>=live[t][i]+live[t+1][i]-r-1)
        def local_memory(i,condition=None):
            local={i}|{idx[d] for d in ns[i]['deps'] if d in idx}
            local_units=sum(ns[j]['bytes']//unit for j in local)
            lhs=fixed//unit+local_units+sum(ns[j]['bytes']//unit*pv for j,pv in persistent.items() if j not in local)
            # P is a subset of either endpoint's live set. This exact big-M is
            # therefore sufficient to disable the extra local-allocation cut.
            m.add(lhs<=cap//unit+(local_units*(1-condition) if condition is not None else 0))
        for i,r in row.items():
            if not ns[i]['recomputable']:m.add(r==0)
            if i in live[t+1]:m.add(live[t+1][i]<=live[t][i]+r)
            for d in ns[i]['deps']:
                if d in idx:
                    j=idx[d]
                    assert j in row # S_t is ancestor closed.
                    m.add(r<=live[t][j]+row[j])
            costs.append(ns[i]['cost']//costunit*r)
            if persistent_allocations:local_memory(i,r)
        # New guaranteed-seen nodes need not first execute in this interval.
        # Prefetched parallel branches are a crucial counterexample to the naive
        # unconditional rule. A descendant of this first-forward pivot cannot
        # have executed before that pivot's first output allocation.
        for i in range(n):
            bit=1<<i
            new=bool(b['seen']&bit and not a['seen']&bit)
            after=a['kind']=='forward' and bool(anc[i]&(1<<idx[a['node']]))
            if new and (naive or after):
                if persistent_allocations:local_memory(i)
                for d in ns[i]['deps']:
                    if d in idx and a['seen']&(1<<idx[d]):
                        j=idx[d];m.add(live[t][j]+row[j]>=1)
    work=sum(costs)
    if budget is not None:m.add(work<=budget//costunit)
    m.minimize(work)
    if hint:
        for t,row in enumerate(live):
            for i,v in row.items():m.add_hint(v,int(bool(hint['live'][t]&(1<<i))))
        for t,row in enumerate(regen):
            for i,v in row.items():m.add_hint(v,int(bool(hint['regen'][t]&(1<<i))))
    return m,cuts,live,regen,costunit


def check_mapping(graph, pivots, cap, cert,qk_backward_cut=False,persistent_allocations=False):
    cuts,anc=events(graph,pivots,qk_backward_cut);given=mapping(graph,cuts,cert)
    model,cuts,live,regen,costunit=build(graph,pivots,cap,cert['budget'],qk_backward_cut=qk_backward_cut,persistent_allocations=persistent_allocations)
    for t,row in enumerate(live):
        for i,v in row.items():model.add(v==int(bool(given['live'][t]&(1<<i))))
    for t,row in enumerate(regen):
        for i,v in row.items():model.add(v==int(bool(given['regen'][t]&(1<<i))))
    solver=cp_model.CpSolver();solver.parameters.num_search_workers=1;solver.parameters.max_time_in_seconds=30;solver.parameters.max_memory_in_mb=300
    status=solver.solve(model)
    assert status in (cp_model.OPTIMAL,cp_model.FEASIBLE),solver.status_name(status)
    charged=sum(ns['cost'] for t,r in enumerate(given['regen']) for i,ns in enumerate(graph['nodes']) if r&(1<<i))
    assert charged<=given['actual_recompute_cost']
    return dict(status=solver.status_name(status),mapped_interval_charge=charged,actual_cost=given['actual_recompute_cost'],events=len(cuts))


def solve(graph,pivots,cap,budget=None,seconds=120,naive=False,hint=None,strategy='default',qk_backward_cut=False,persistent_allocations=False,progress=False):
    if type(seconds) not in (int,float) or not math.isfinite(seconds) or seconds<=0:raise ValueError('positive finite time limit required')
    model,cuts,live,regen,costunit=build(graph,pivots,cap,budget,naive=naive,hint=hint,qk_backward_cut=qk_backward_cut,persistent_allocations=persistent_allocations)
    solver=cp_model.CpSolver();solver.parameters.num_search_workers=1;solver.parameters.max_time_in_seconds=seconds
    solver.parameters.max_memory_in_mb=300
    solver.parameters.random_seed=20261021
    if strategy=='lp':solver.parameters.linearization_level=2
    elif strategy=='core':
        solver.parameters.optimize_with_core=True
        solver.parameters.linearization_level=0
    elif strategy!='default':raise ValueError('unknown search strategy')
    if hint is not None:
        solver.parameters.repair_hint=True
        solver.parameters.hint_conflict_limit=10000
    started=time.monotonic()
    if progress:
        solver.best_bound_callback=lambda bound: print(json.dumps(dict(kind='bound_progress',raw_work_bound=bound*costunit,seconds=time.monotonic()-started)),flush=True)
    status=solver.solve(model)
    stats=dict(status=solver.status_name(status),cap=cap,budget=budget,events=len(cuts),
               seconds=time.monotonic()-started,solver='OR-Tools '+ortools.__version__,
               workers=1,time_limit_seconds=seconds,strategy=strategy,qk_backward_cut=qk_backward_cut,persistent_allocations=persistent_allocations,solver_memory_limit_mb=300,naive_newnode_rule=naive,
               scope='ordered necessary-event relaxation; feasible result is not a legal schedule',
               certified_global_lower_bound=None,raw_best_bound=solver.best_objective_bound*costunit)
    if status in (cp_model.OPTIMAL,cp_model.FEASIBLE):
        objective=sum(graph['nodes'][i]['cost']*solver.value(v) for row in regen for i,v in row.items())
        stats['relaxation_work']=objective
        stats['live']=[sum(1<<i for i,v in row.items() if solver.value(v)) for row in live]
        stats['regen']=[sum(1<<i for i,v in row.items() if solver.value(v)) for row in regen]
        if status==cp_model.OPTIMAL and not naive:stats['certified_global_lower_bound']=objective
    return stats


def transformer_pivots(graph):
    ids={v['id'] for v in graph['nodes']}
    suffixes=('norm1','scores','probs','context','proj','residual1','norm2','up','gelu','down','residual2')
    result=[];b=0
    while f'b{b}_norm1' in ids:
        result += [f'b{b}_{s}' for s in suffixes];b+=1
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--graph',required=True);p.add_argument('--cap',type=int,required=True)
    p.add_argument('--budget',type=int);p.add_argument('--seconds',type=float,default=120)
    p.add_argument('--witness');p.add_argument('--hint-witness');p.add_argument('--out',required=True)
    p.add_argument('--strategy',choices=('default','lp','core'),default='default')
    p.add_argument('--qk-backward-cut',action='store_true')
    p.add_argument('--persistent-allocations',action='store_true')
    p.add_argument('--progress',action='store_true')
    args=p.parse_args();g=load(args.graph);pivots=transformer_pivots(g)
    hint=None
    if args.witness:
        c=load(args.witness);print(json.dumps(check_mapping(g,pivots,args.cap,c,args.qk_backward_cut,args.persistent_allocations)),flush=True)
        hint=mapping(g,events(g,pivots,args.qk_backward_cut)[0],c)
    if args.hint_witness:
        c=load(args.hint_witness);verify(g,c,c['budget'])
        hint=mapping(g,events(g,pivots,args.qk_backward_cut)[0],c)
    result=solve(g,pivots,args.cap,args.budget,args.seconds,hint=hint,strategy=args.strategy,qk_backward_cut=args.qk_backward_cut,persistent_allocations=args.persistent_allocations,progress=args.progress)
    Path(args.out).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('live','regen')},sort_keys=True),flush=True)


if __name__=='__main__':main()
