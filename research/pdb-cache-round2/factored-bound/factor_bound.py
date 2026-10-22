"""Necessary common-region bound, factored by owned bytes and future minima."""
INF=(1<<32)-1

def owned_units(nodes,unit):
    assert len(nodes)==14 and unit>0
    assert all(v['bytes']%unit==0 for v in nodes)
    memory=[0]*16384
    for live in range(1,16384):
        bit=live&-live
        memory[live]=memory[live^bit]+nodes[bit.bit_length()-1]['bytes']//unit
    return memory

def summaries(cap,demand,terminal,cost_unit,memory):
    """A uses exact current owned size; E and Z use at-most owned size."""
    maximum=max(memory)
    A=[None]*(maximum+1);A_masks=[None]*(maximum+1)
    for live,value in enumerate(demand):
        if value==INF:continue
        r=memory[live];cost=int(value)*cost_unit
        if A[r] is None or cost<A[r]:A[r]=cost;A_masks[r]=live
    E=[];E_masks=[]
    for m in range(maximum+1):
        previous=None if m==0 else E[m-1]
        if A[m] is not None and (previous is None or A[m]<previous):E.append(A[m]);E_masks.append(A_masks[m])
        else:E.append(previous);E_masks.append(None if m==0 else E_masks[m-1])
    Z={};Z_masks={};forced=(1<<10)|(1<<11)
    for c,values in terminal.items():
        costs=[None]*(maximum+1);masks=[None]*(maximum+1)
        # First12 seen; DOWN absent. Both UP and GELU must currently be live.
        for live in range(4096):
            if live&forced!=forced or values[live]==INF:continue
            s=memory[live];cost=int(values[live])*cost_unit
            if costs[s] is None or cost<costs[s]:costs[s]=cost;masks[s]=live
        for s in range(1,maximum+1):
            if costs[s-1] is not None and (costs[s] is None or costs[s-1]<costs[s]):costs[s]=costs[s-1];masks[s]=masks[s-1]
        Z[c]=costs;Z_masks[c]=masks
    return dict(A=A,E=E,Z=Z,A_masks=A_masks,E_masks=E_masks,Z_masks=Z_masks)

def minimize(A,E,Z,cap,clip_cap,regions=3):
    """Min-plus convolution; every feasible (r_i,m_i) tuple is represented."""
    assert cap>=9 and len(A)==len(E) and clip_cap>=9
    dp={(0,0):(0,[])};stages=[];transitions=0
    for block in range(regions):
        nxt={}
        for (M,R),(cost,path) in dp.items():
            for r in range(min(len(A)-1,cap-9-R)+1):
                if A[r] is None:continue
                for m in range(r+1):
                    if E[m] is None:continue
                    transitions+=1;key=(M+m,R+r);value=cost+max(A[r],E[m])
                    if key not in nxt or value<nxt[key][0]:nxt[key]=(value,path+[(r,m)])
        dp=nxt;stages.append(len(dp))
    best=None;argmin=None
    for (M,R),(cost,path) in dp.items():
        assert 0<=M<=R<=cap-9
        physical_cap=cap-M;c=min(physical_cap,clip_cap);s=cap-1-R
        z=Z[c][min(s,len(Z[c])-1)]
        if z is None:continue
        total=cost+z
        if best is None or total<best:
            best=total;argmin=dict(M=M,R=R,allocation=path,target_physical_cap=physical_cap,target_table_cap=c,target_owned_allowance=s,prior_bound=cost,target_bound=z)
    return dict(lower_bound=best,argmin=argmin,states_by_stage=stages,transitions=transitions)
