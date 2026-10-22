"""Nested output-read endpoint factor price; graph/table semantics are external.

A[c][r] is a minimum output-demand cost at exact current owned size r.
E[c][m] is its at-most-m envelope. Z[c][s] is a terminal-phase minimum
with the forced final UP/GELU live and at most s current owned units.
None means unreachable. Clipping capacities requires a separately proved
transition-graph saturation; this kernel does not infer it from the arrays.
"""


def _validate(cap, A, E, Z, clip_cap):
    if type(cap) is not int or cap < 9:
        raise ValueError('standing input and final UP/GELU require at least9')
    if type(clip_cap) is not int or clip_cap < 9:
        raise ValueError('clip_cap must be an integral supported capacity')
    rows = range(9, min(cap, clip_cap) + 1)
    for c in rows:
        if c not in A or c not in E or c not in Z:
            raise ValueError('missing attainable capacity row')
        if not A[c] or len(A[c]) != len(E[c]) or not Z[c]:
            raise ValueError('invalid owned-size domains')
        values = list(A[c]) + list(E[c]) + list(Z[c])
        if any(v is not None and (type(v) is not int or v < 0) for v in values):
            raise ValueError('nonnegative exact integers or None required')
        best = None
        for r, value in enumerate(A[c]):
            if value is not None and (best is None or value < best):
                best = value
            if E[c][r] != best:
                raise ValueError('E must be the prefix minimum of A')


def minimize_nested(cap, A, E, Z, *, clip_cap):
    """Exact min-convolution over all three current-size/future-minimum pairs."""
    _validate(cap, A, E, Z, clip_cap)
    dp = {(0, 0): (0, [])}
    stages = []
    transitions = 0
    for _ in range(3):
        following = {}
        for (M, R), (cost, path) in dp.items():
            # Earlier minima persist through this owner's entire completion.
            c = min(cap - M, clip_cap)
            assert c >= 9
            for r in range(min(len(A[c]) - 1, cap - 9 - R) + 1):
                if A[c][r] is None:
                    continue
                for m in range(r + 1):
                    if E[c][m] is None:
                        continue
                    transitions += 1
                    key = M + m, R + r
                    value = cost + max(A[c][r], E[c][m])
                    if key not in following or value < following[key][0]:
                        following[key] = value, path + [(r, m)]
        dp = following
        stages.append(len(dp))
    best = None
    argmin = None
    for (M, R), (cost, path) in dp.items():
        assert 0 <= M <= R <= cap - 9
        c = min(cap - M, clip_cap)
        s = cap - 1 - R
        z = Z[c][min(s, len(Z[c]) - 1)]
        if z is None:
            continue
        total = cost + z
        if best is None or total < best:
            best = total
            argmin = dict(M=M, R=R, allocation=path, prior_bound=cost,
                          target_table_cap=c, target_physical_cap=cap-M,
                          target_owned_allowance=s, target_bound=z)
    return dict(lower_bound=best, argmin=argmin, states_by_stage=stages,
                transitions=transitions)


def enumerate_nested(cap, A, E, Z, *, clip_cap,
                     maximum_configurations=1500000):
    """Separate six-coordinate enumeration, with no aggregate-state DP."""
    _validate(cap, A, E, Z, clip_cap)
    limit = cap - 9
    best = None
    argmin = None
    count = 0
    c0 = min(cap, clip_cap)
    for r0 in range(min(limit, len(A[c0])-1) + 1):
        if A[c0][r0] is None:
            continue
        for m0 in range(r0 + 1):
            c1 = min(cap - m0, clip_cap)
            for r1 in range(min(limit-r0, len(A[c1])-1) + 1):
                if A[c1][r1] is None:
                    continue
                for m1 in range(r1 + 1):
                    c2 = min(cap - m0 - m1, clip_cap)
                    for r2 in range(min(limit-r0-r1, len(A[c2])-1) + 1):
                        if A[c2][r2] is None:
                            continue
                        for m2 in range(r2 + 1):
                            count += 1
                            if count > maximum_configurations:
                                raise RuntimeError('enumeration limit; no exact price')
                            terms = (E[c0][m0], E[c1][m1], E[c2][m2])
                            if None in terms:
                                continue
                            c3 = min(cap-m0-m1-m2, clip_cap)
                            s = cap-1-r0-r1-r2
                            z = Z[c3][min(s, len(Z[c3])-1)]
                            if z is None:
                                continue
                            value = (max(A[c0][r0], terms[0]) +
                                     max(A[c1][r1], terms[1]) +
                                     max(A[c2][r2], terms[2]) + z)
                            if best is None or value < best:
                                best = value
                                argmin = dict(r=[r0,r1,r2], m=[m0,m1,m2])
    return dict(lower_bound=best, argmin=argmin, configurations=count)
