"""Separate algebra and full-certificate owned-work controls."""
import copy,random
from verifier import verify,Invalid,digest
from factor_bound import minimize,enumerate_direct,INF

def tiny_factoring():
    rng=random.Random(2026102202);count=0
    for cap in range(9,17):
        for _ in range(8):
            A=[rng.randrange(500) if i==0 or rng.randrange(4) else None for i in range(7)]
            E=[min(v for v in A[:m+1] if v is not None) for m in range(7)]
            Z={}
            for c in range(9,cap+1):
                row=[None]*8;best=None
                for s in range(8,cap):
                    value=rng.randrange(500);best=value if best is None else min(best,value);row.append(best)
                Z[c]=row
            assert minimize(cap,A,E,Z,cap)['lower_work']==enumerate_direct(cap,A,E,Z,cap)['lower_work'];count+=1
    bad=list(E);bad[0]+=1;rejected=[]
    for name,args in [('wrong_prefix',(A,bad,Z)),('negative_cost',([-1]+A[1:],E,Z)),('missing_cap',(A,E,{c:v for c,v in Z.items() if c!=9}))]:
        try:minimize(cap,*args,cap)
        except ValueError:rejected.append(name)
        else:raise AssertionError('Accepted summary forgery '+name)
    return dict(random_direct_comparisons=count,input_forgeries=rejected)

def all_nineteen_roots(graph,memory,demand,terminal,cost_unit,lower):
    nodes=graph['nodes'];fixed=(1<<24)|(1<<25)
    options=[i for i in range(26) if not(fixed>>i&1) and nodes[i]['bytes']==65536]
    assert len(options)==18
    best=None;roots=0
    for optional in [None]+options:
        live=fixed|(0 if optional is None else 1<<optional);left=live&16383;right=(live>>14)&16383;r=memory[left]
        current=int(demand[left])*cost_unit;value=None
        for m in range(r+1):
            candidates=[int(v)*cost_unit for mask,v in enumerate(demand) if memory[mask]<=m and v!=INF]
            if not candidates:continue
            z=terminal[10-m][right]
            if z==INF:continue
            total=max(current,min(candidates))+int(z)*cost_unit;value=total if value is None else min(value,total)
        assert value is not None and value>=lower
        best=value if best is None else min(best,value);roots+=1
    assert roots==19 and best==lower==106725376
    return dict(roots=roots,minimum=best)

def actual_components(graph,certificate,C,memory,demand,terminal,cost_unit,summary,lower):
    metrics,trace=verify(graph,certificate,certificate['budget'],True)
    assert metrics['peak_bytes']<=C*65536
    actions=certificate['actions'];nodes=graph['nodes'];index={v['id']:i for i,v in enumerate(nodes)}
    root=next(i for i,a in enumerate(actions) if a==dict(op='forward',node='b1_gelu'))
    endpoint=next(i for i,a in enumerate(actions) if a==dict(op='backward',node='b1_norm1'))
    assert root<endpoint and trace[root]['recompute_cost']==0
    firsts={index[a['node']] for a in actions[:root+1] if a['op']=='forward'}
    assert firsts==set(range(26)) and not any(a['op']=='backward' for a in actions[:root+1])
    live=sum(1<<index[x] for x in trace[root]['live'] if x in index);left=live&16383;right=(live>>14)&16383
    r=memory[left];m=min(sum(nodes[index[x]]['bytes']//65536 for x in trace[t]['live'] if x in index and index[x]<14) for t in range(root,endpoint))
    remaining=[0,0];seen=set()
    for t,a in enumerate(actions):
        if a['op']=='forward':
            i=index[a['node']]
            if t>root and i in seen:remaining[i//14]+=nodes[i]['cost']
            seen.add(i)
    current=int(demand[left])*cost_unit;owner=max(current,summary['E'][m]);small=max(summary['A'][r],summary['E'][m])
    target_cap=min(23,C-m);target=int(terminal[target_cap][right])*cost_unit
    z=summary['Z'][target_cap][min(C-1-r,len(summary['Z'][target_cap])-1)]
    assert small<=owner<=remaining[0] and z<=target<=remaining[1]
    assert lower<=small+z<=owner+target<=sum(remaining)==metrics['recompute_cost']
    assert lower==metrics['recompute_cost']
    return dict(metrics=metrics,current_r=r,future_minimum_m=m,owned_remaining=remaining,identity_sensitive_bounds=[owner,target],factored_actual_case=[small,z],prefix_work=0)

def witness_forgeries(graph,certificate):
    rejected=[]
    for kind in ['foreign_graph_cost','underclaim','one_below_work','missing_regeneration']:
        changed=copy.deepcopy(certificate);g=graph
        if kind=='foreign_graph_cost':g=copy.deepcopy(graph);g['nodes'][0]['cost']+=1
        elif kind=='underclaim':changed['claims']['recompute_cost']-=1
        elif kind=='one_below_work':changed['budget']=changed['claims']['recompute_cost']-1
        else:
            seen=set()
            for at,a in enumerate(changed['actions']):
                if a['op']!='forward':continue
                if a['node'] in seen:del changed['actions'][at];break
                seen.add(a['node'])
        try:verify(g,changed,changed['budget'])
        except Invalid as error:rejected.append(dict(change=kind,status='REJECTED',reason=str(error)))
        else:raise AssertionError('Accepted witness forgery '+kind)
    return rejected
