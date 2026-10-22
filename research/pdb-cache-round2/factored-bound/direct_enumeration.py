"""Direct six-coordinate check of a three-region factored cut price.

This is separate from the min-convolution DP: enumerate r0,r1,r2 and
m0,m1,m2 explicitly. A[r] is an exact-current-size minimum; E[m] its
at-most-m prefix minimum. Z[c][s] is an at-most-s last-region minimum.
None denotes unreachable. Z rows saturate above their final owned-size index.
Callers establish graph/table semantics and any cap clipping separately.
"""
import math

def enumerate_price(cap,A,E,Z,*,fixed_units=1,forced_units=8,
                    maximum_configurations=1500000):
    if type(cap) is not int or cap<fixed_units+forced_units:
        raise ValueError('cap cannot fit the standing input and forced values')
    if len(A)!=len(E) or not A:
        raise ValueError('A and E must have the same nonempty owned-size domain')
    for value in list(A)+list(E)+[v for row in Z.values() for v in row]:
        if value is not None and (type(value) is not int or value<0):
            raise ValueError('integer nonnegative prices or None required')
    prices=[math.inf if x is None else x for x in A]
    envelopes=[math.inf if x is None else x for x in E]
    if envelopes!=[min(prices[:m+1]) for m in range(len(prices))]:
        raise ValueError('E is not the at-most-size prefix envelope of A')
    lowcap=fixed_units+forced_units
    if any(c not in Z or not Z[c] for c in range(lowcap,cap+1)):
        raise ValueError('every attainable target capacity needs a Z row')
    best=math.inf;argmin=None;configurations=0
    current_limit=cap-fixed_units-forced_units
    for r0 in range(min(len(A)-1,current_limit)+1):
        if prices[r0]==math.inf:continue
        for r1 in range(min(len(A)-1,current_limit-r0)+1):
            if prices[r1]==math.inf:continue
            for r2 in range(min(len(A)-1,current_limit-r0-r1)+1):
                if prices[r2]==math.inf:continue
                current=r0+r1+r2;allowance=cap-fixed_units-current
                for m0 in range(r0+1):
                    for m1 in range(r1+1):
                        for m2 in range(r2+1):
                            configurations+=1
                            if configurations>maximum_configurations:
                                raise RuntimeError('direct-enumeration limit; no exact price')
                            reserved=m0+m1+m2;targetcap=cap-reserved
                            row=Z[targetcap]
                            last=row[min(allowance,len(row)-1)]
                            if last is None:continue
                            value=(max(prices[r0],envelopes[m0])+
                                   max(prices[r1],envelopes[m1])+
                                   max(prices[r2],envelopes[m2])+last)
                            if value<best:
                                best=value
                                argmin=dict(r=[r0,r1,r2],m=[m0,m1,m2],
                                            R=current,M=reserved,lastcap=targetcap,
                                            lastownedallowance=allowance)
    return dict(minimum=None if best==math.inf else best,argmin=argmin,
                direct_six_coordinate_configurations=configurations)
