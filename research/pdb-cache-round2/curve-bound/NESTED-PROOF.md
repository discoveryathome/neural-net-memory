# Nested endpoint extension of the factored cut bound

This is an author-checked extension. The local exact tables,
their audits, and the common first-final-GELU cut mapping remain prerequisites.
The new file `nested_bound.py` changes only the capacity assigned to the three
earlier owners. It does not change a graph transition or the frozen common
kernel. All arithmetic is integral. A matching full legal schedule is needed
before calling a lower price an attained minimum.

Let t0 be immediately after the first final-block GELU allocation. All earlier
blocks'14 first forwards are complete; the final first12 are complete, DOWN
and RES2 are unseen. All backwards remain pending. Immutable x owns1 unit,
and final UP/GELU own8. For earlier block i in {0,1,2}, let e_i be the state
immediately BEFORE the backward of norm1 in block i+1 reads block i's output.
These states are strictly ordered e_2 < e_1 < e_0 by consumer readiness.
The endpoint is before the read, so a drop after that read cannot lower m_i.

Define r_i as block i's owned live units at t0, and m_i as its minimum owned
units over all states from t0 through e_i inclusive. Hence0<=m_i<=r_i and
R=sum(r_i)<=C-9. The minimum may occur anywhere, including after a forward
allocation or drop; every finite trace supplies a state attaining it.

For block b, the entire projection needed to satisfy its output demand and
complete its own backwards ends no later than its own norm1 backward. For
each i<b, that action is at or before e_i: for i=b-1 it is exactly e_i, and
for older i it is earlier. Therefore all those earlier regions retain at
least m_i units throughout that entire projection. They are disjoint owned
value sets, and immutable x remains live, so block b has a favorable local
cap c_b=C-sum(m_i for i<b), including the local standing input unit that
stands for global immutable x. Other outside allocations are ignored, and
the block entry is always freely available. This can only weaken the bound.

No own backward of block b has happened by e_b: its output's downstream
consumer norm1 has not yet run. Thus, both at t0 and at a state attaining
m_b, all own backwards and the output demand are pending, and all own first
forwards have already happened. If W_b is future work owned by this block,

    W_b >= max(D_c_b[L_b(t0)], E_c_b[m_b])
        >= max(A_c_b[r_b], E_c_b[m_b]).

The second term is a suffix of the same owned work. Taking max avoids double
counting. Prefixing A by owned-size and minimizing current identities is a
favorable relaxation, not an assumption that those identities are reachable
for free. Local entry recomputations have no owned cost and no extra memory,
which is favorable even when the actual entry is expensive.

For the final block, every earlier m_i persists through completion of its
projection, since e_i is no earlier than the final norm1 backward. Its cap
is C-M, M=sum(m_i), and its initial owned allowance is C-1-R. The existing
terminal-phase table therefore supplies Z_(C-M)(C-1-R). All four owned cost
sets are disjoint. The original prefix's repeated-forward work is nonnegative
and may be discarded. Every legal trace supplies an included six-coordinate
tuple, proving the minimum over those tuples is a necessary global bound.

The DP processes earlier blocks in ascending order. A partial tuple needs only
M=sum(previous minima) and R=sum(previous current units). The next owner's
cost uses c=C-M and max(A_c[r],E_c[m]); update(M+m,R+r). Thus aggregate-state
merging does not lose relevant information. The final term uses that same M
and R. All attainable capacities are >=9 because M<=R<=C-9. Any clipping at27
uses the existing exact all14-live saturation proof; a floor9 is unnecessary
and is not used. The portable direct checker instead enumerates all six
coordinates without DP, selecting c0,c1,c2,c3 separately.

Controls from newly built exact local tables9..15 agree across the private
explicit DP, portable DP, and separate six-coordinate enumeration:

| C | Necessary nested price | Current schedule work |
|---|---:|---:|
|11|524,877,824|702,349,312|
|12|463,929,344|no feasible original budget478,150,656 schedule at12u; separately excluded|
|13|405,864,448|421,494,784|
|14|354,451,456|355,270,656|
|15|312,147,968|312,147,968|

C12 matches the separately enumerated9178 critical-root nested price.
C15 reaches the full legal curve schedule. C14 retains819,200 headroom;
matching one chosen tuple cannot exclude a cheaper tuple. The tuple atC14
uses successive owned caps14/13/12, r=m=(1,1,1), and final cap11. Its costs
are95,322,112+103,710,720+111,280,128+44,138,496=354,451,456.

Earlier generic tests independently computed unreduced global tails and all
tiny local D/output-demand tables on240 seeded two/three-block graphs. They
checked the identity-sensitive nested theorem, including actual endpoints
and owned-cost components, against exact optima and the unchanged full
verifier. That is useful stress evidence, not independent scientific review.
See `resnet-work/test_generic_region_bounds.py` and its JSON receipt.

Credit follows the existing package: Doug Colkitt (@Mister-Meeseeks), the
original model/verifier and trial code, regional predecessors PR6/PR10/PR11,
and the common factor/curve work by the same Codex author team. This extension
was generated and checked by Codex; no independent human validation is claimed.

`nested_replay.py --repo ROOT --out OUT` runs the full common joint proof once,
then this extension. Programmatic `run(repo,out,shared=(common_out,result))`
reuses `joint_replay.run` from that same replay process. It does not accept a
CLI shortcut around the common audits. The new demand tables at9/10 are
regenerated, hash-pinned, audited against all forward edges with tight paths,
and subjected to four rehashed semantic forgeries. The other consumed tables
are the audited and hash-pinned common replay outputs. Twenty-eight random
factor controls compare DP with separate six-coordinate enumeration and
reject four invalid summary inputs. The generated C14/C15 full certificates
also check own-read endpoints, reduced capacities, and each disjoint owned
cost component; C15 reaches equality. The combined result has68 exact caps
15..82, a remaining C14 gap819,200, and no additional fixed benchmark wins.

The fully audited terminal table at9u also proves a universal10u peak floor
for this graph, at any repeated-forward budget. All1024 first12 live masks
containing final UP/GELU have unreachable phase0 values at9u. Every legal
complete schedule passes the first-final-GELU cut; ignoring outside regions,
freeing the local entry, charging only immutable x, and omitting earlier
owners' work gives precisely this favorable terminal problem. Its
unreachability excludes any global9u schedule. Capacities below9u cannot
allocate UP/GELU together with x. This is an auxiliary universal floor and
does not count as another original benchmark win.
