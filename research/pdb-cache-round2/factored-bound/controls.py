"""Independent algebra controls and legal-continuation checks for factoring."""
import copy,itertools,random
from factor_bound import minimize,INF
from direct_enumeration import enumerate_price
from verifier import verify,digest,Invalid

def tiny_factoring():
    rng=random.Random(20261022);count=0
    for cap in range(9,14):
        for repeat in range(6):
            A=[rng.randrange(500) if i==0 or rng.randrange(4) else None for i in range(4)]
            E=[]
            for i in range(len(A)):
                finite=[v for v in A[:i+1] if v is not None];E.append(min(finite) if finite else None)
            Z={}
            for c in range(9,cap+1):
                row=[None]*8;current=None
                for s in range(8,cap):
                    value=rng.randrange(500);current=value if current is None else min(current,value);row.append(current)
                Z[c]=row
            dynamic=minimize(A,E,Z,cap,cap)
            direct=enumerate_price(cap,A,E,Z)
            assert dynamic['lower_bound']==direct['minimum']
            count+=1
    bad=list(E);bad[0]+=1
    for name,args in [('wrong_prefix_envelope',(A,bad,Z)),('negative_price',([-1]+A[1:],E,Z)),('missing_cap_row',(A,E,{k:v for k,v in Z.items() if k!=9}))]:
        try:enumerate_price(cap,*args)
        except ValueError:continue
        raise AssertionError('Accepted factor-input forgery '+name)
    return dict(tiny_brute_comparisons=count,input_forgeries_rejected=3)

def all_9178_roots(graph,memory,demand,terminal,cost_unit,lower_bound):
    nodes=graph['nodes'];unit=graph['inputs'][0]['bytes'];forced=(1<<52)|(1<<53)
    options=[i for i in range(54) if not(forced>>i&1) and nodes[i]['bytes']==unit]
    assert len(options)==38
    E=[]
    for m in range(4):E.append(min(int(demand[lv])*cost_unit for lv in range(16384) if memory[lv]<=m and demand[lv]!=INF))
    minimum=None;roots=cases=0
    for count in range(4):
        for chosen in itertools.combinations(options,count):
            live=forced|sum(1<<i for i in chosen);local=[(live>>(14*b))&16383 for b in range(4)]
            r=[memory[v] for v in local[:3]];current=[int(demand[v])*cost_unit for v in local[:3]];best=None
            for m in itertools.product(*(range(v+1) for v in r)):
                cases+=1;c=12-sum(m);value=terminal[c][local[3]&8191]
                if value==INF:continue
                total=sum(max(current[b],E[m[b]]) for b in range(3))+int(value)*cost_unit
                best=total if best is None else min(best,total)
            assert best is not None and lower_bound<=best
            minimum=best if minimum is None else min(minimum,best);roots+=1
    assert roots==9178 and minimum==462716928==lower_bound
    return dict(roots=roots,minimum_cases=cases,minimum=minimum)

def actual_components(graph,certificate,cap,memory,demand,terminal,cost_unit,summary,price):
    metrics,trace=verify(graph,certificate,certificate['budget'],True)
    assert metrics['peak_bytes']<=cap*graph['inputs'][0]['bytes']
    nodes=graph['nodes'];index={v['id']:i for i,v in enumerate(nodes)}
    root=next(i for i,a in enumerate(certificate['actions']) if a==dict(op='forward',node='b3_gelu'))
    endpoint=next(i for i,a in enumerate(certificate['actions']) if a==dict(op='backward',node='b3_norm1'))
    assert trace[root]['recompute_cost']==0
    firsts={index[a['node']] for a in certificate['actions'][:root+1] if a['op']=='forward'}
    assert firsts==set(range(54)) and not any(a['op']=='backward' for a in certificate['actions'][:root+1])
    live=sum(1<<index[x] for x in trace[root]['live'] if x in index)
    local=[(live>>(14*b))&16383 for b in range(4)]
    r=[memory[lv] for lv in local[:3]]
    m=[min(sum(nodes[index[x]]['bytes'] for x in trace[at]['live'] if x in index and index[x]//14==b)//graph['inputs'][0]['bytes'] for at in range(root,endpoint)) for b in range(3)]
    remaining=[0]*4;seen=set()
    for at,action in enumerate(certificate['actions']):
        if action['op']=='forward':
            i=index[action['node']]
            if at>root and i in seen:remaining[i//14]+=nodes[i]['cost']
            seen.add(i)
    full=[];compressed=[]
    for b in range(3):
        h=int(demand[local[b]])*cost_unit
        exact=max(h,summary['E'][m[b]])
        small=max(summary['A'][r[b]],summary['E'][m[b]])
        assert small<=exact<=remaining[b]
        full.append(exact);compressed.append(small)
    targetcap=min(27,cap-sum(m));active=int(terminal[targetcap][local[3]&8191])*cost_unit
    allowance=cap-1-sum(r);z=summary['Z'][targetcap][min(allowance,len(summary['Z'][targetcap])-1)]
    assert z<=active<=remaining[3]
    assert price['lower_bound']<=sum(compressed)+z<=sum(full)+active<=sum(remaining)
    assert price['lower_bound']==sum(remaining)==metrics['recompute_cost']
    return dict(certificate_sha256=digest(certificate),metrics=metrics,current_r=r,actual_minima=m,actual_owned_remaining=remaining,factored_actual_case=compressed+[z],uncompressed_actual_case=full+[active],first_gelu_prefix_work=0)

def witness_forgeries(graph,certificate):
    receipts=[]
    for kind in ['graph_cost','underclaimed_work','one_below_work','omitted_regeneration']:
        changed=copy.deepcopy(certificate);g=graph
        if kind=='graph_cost':g=copy.deepcopy(graph);g['nodes'][0]['cost']+=1
        elif kind=='underclaimed_work':changed['claims']['recompute_cost']-=1
        elif kind=='one_below_work':changed['budget']=changed['claims']['recompute_cost']-1
        else:
            seen=set()
            for at,action in enumerate(changed['actions']):
                if action['op']!='forward':continue
                if action['node'] in seen:del changed['actions'][at];break
                seen.add(action['node'])
        try:verify(g,changed,changed['budget'])
        except Invalid as error:receipts.append(dict(change=kind,status='REJECTED',reason=str(error)))
        else:raise AssertionError('Accepted witness forgery '+kind)
    return receipts
