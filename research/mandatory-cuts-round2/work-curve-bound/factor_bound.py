"""Two-owner specialization of the credited factored mandatory-cut bound."""
INF=(1<<32)-1

def owned_units(nodes,unit):
    assert len(nodes)==14 and unit>0 and all(v['bytes']%unit==0 for v in nodes)
    memory=[0]*16384
    for live in range(1,16384):
        bit=live&-live
        memory[live]=memory[live^bit]+nodes[bit.bit_length()-1]['bytes']//unit
    return memory

def summaries(demand,terminal,cost_unit,memory):
    """A uses exact owned size; E and Z use at-most owned size."""
    maximum=max(memory);A=[None]*(maximum+1);A_masks=[None]*(maximum+1)
    for live,value in enumerate(demand):
        if value==INF:continue
        r=memory[live];cost=int(value)*cost_unit
        if A[r] is None or cost<A[r]:A[r]=cost;A_masks[r]=live
    E=[]
    for m in range(maximum+1):
        finite=[v for v in A[:m+1] if v is not None]
        E.append(min(finite) if finite else None)
    Z={};Z_masks={};forced=(1<<10)|(1<<11)
    for cap,values in terminal.items():
        row=[None]*(maximum+1);masks=[None]*(maximum+1)
        for live in range(4096):
            if live&forced!=forced or values[live]==INF:continue
            s=memory[live];cost=int(values[live])*cost_unit
            if row[s] is None or cost<row[s]:row[s]=cost;masks[s]=live
        for s in range(1,maximum+1):
            if row[s-1] is not None and (row[s] is None or row[s-1]<row[s]):row[s]=row[s-1];masks[s]=masks[s-1]
        Z[cap]=row;Z_masks[cap]=masks
    return dict(A=A,E=E,Z=Z,A_masks=A_masks,Z_masks=Z_masks)

def validate(C,A,E,Z,clip_cap):
    if type(C) is not int or C<9 or type(clip_cap) is not int or clip_cap<9:raise ValueError('invalid capacity')
    if not A or len(A)!=len(E):raise ValueError('invalid owned-size domain')
    for c in range(9,min(C,clip_cap)+1):
        if c not in Z or not Z[c]:raise ValueError('missing terminal capacity')
    if any(v is not None and (type(v) is not int or v<0) for row in [A,E]+list(Z.values()) for v in row):raise ValueError('nonnegative exact prices required')
    for m in range(len(A)):
        finite=[v for v in A[:m+1] if v is not None]
        if E[m]!=(min(finite) if finite else None):raise ValueError('invalid prefix minimum')

def minimize(C,A,E,Z,clip_cap):
    """One min-plus stage retaining (future minimum,current owned size)."""
    validate(C,A,E,Z,clip_cap);states={};transitions=0
    for r in range(min(len(A)-1,C-9)+1):
        if A[r] is None:continue
        for m in range(r+1):
            if E[m] is None:continue
            states[m,r]=max(A[r],E[m]);transitions+=1
    best=None;argmin=None
    for (m,r),cost in states.items():
        c=min(C-m,clip_cap);s=C-1-r;z=Z[c][min(s,len(Z[c])-1)]
        if z is None:continue
        total=cost+z
        if best is None or total<best:
            best=total;argmin=dict(current_r=r,future_minimum_m=m,prior_bound=cost,target_bound=z,target_physical_cap=C-m,target_table_cap=c,target_owned_allowance=s)
    return dict(lower_work=best,argmin=argmin,states=len(states),transitions=transitions)

def enumerate_direct(C,A,E,Z,clip_cap):
    """Separate literal (r,m) enumeration without an aggregate-state map."""
    validate(C,A,E,Z,clip_cap);best=None;pair=None;cases=0
    for r in range(len(A)):
        for m in range(r+1):
            if r>C-9 or A[r] is None or E[m] is None:continue
            cases+=1;c=min(C-m,clip_cap);s=min(C-1-r,len(Z[c])-1)
            if Z[c][s] is None:continue
            total=max(A[r],E[m])+Z[c][s]
            if best is None or total<best:best=total;pair=[r,m]
    return dict(lower_work=best,argmin_pair=pair,configurations=cases)
