# Complete two-block fixed-memory work curve

This source-only follow-up proves the minimum additional forward work for
`transformer-b2-t64` at all 29 integral memory caps 10..38. The sibling
`work-curve-construction` reconstructs and checks a whole legal schedule at
each bound. The unchanged verifier checks every complete schedule at its
exact additional-work budget. No accepted records, working frontiers, graph,
model, or verifier are changed. Auxiliary points do not count as additional
fixed benchmark wins.

Run from the repository root:

```sh
python3 -B research/mandatory-cuts-round2/work-curve-bound/joint_replay.py \
  --repo . --out /path/to/writable/replay-output
```

The replay uses the standard library and writes generated binaries, tables,
certificates, and results only below `--out`. The calling environment must
permit those writes. It audits all 45 local tables once, shares the canonical
backward tables with the constructor, reconstructs 29 full certificates, and
checks both disjoint owned-cost components against every actual continuation.
The standalone lower replay is `replay.py` with the same options. Table
generation has a 30 second limit and 200,000 state limit per backward table;
limits cause failure, never an impossibility conclusion. The complete public
replay is source-only; no saved binary or 29 action lists are trusted.

The graph is pinned by canonical SHA256
`49253c00a0941d94630e5323343af6e2d19e7317f26864fc19e01bc782bc638b`,
with every local node/input field and the second block's exact renaming
checked. The inherited baseline is
`a95cc1588fc57a07cfcf5a350206825e6f5b4b52`; the round master seed is
`dafc4be0863b7654352ffb2ba4a4d2df`. The lower table and factor computation is
deterministic; synthetic algebra controls use seed 2026102202. These seeds
have different purposes.

At 10u the minimum is 106,725,376; at 13u it is 52,035,584; at 19u it is 26,869,760.
The former 26,804,224 predecessor needs 20u. Zero additional work first becomes
possible at 38u, or 2,490,368 bytes; at 37u the necessary work remains 81,920.
All tensor sizes are multiples of 65,536 bytes, so every legal schedule's peak
is an integral unit and intermediate byte caps have the same feasible set.
`EXPECTED.json` pins all 29 exact prices and 45 raw table hashes. The existing
parent work already treats the original fixed cases; this extension gives
their full work-memory context.

The joint replay also regenerates and checks the credited PR10 last-barrier
cut using the unchanged `reset_cut.py` and `b2-reset-cut.json` copied into the
parent package. Before the first final sink, take the last block0/block1 GELU
barrier. At 9u no other activation survives its UP/GELU plus immutable x;
neither forced state can reach the sink without another such barrier, even
when every other operation has unlimited favorable memory. The exhaustive
finite closure proves a universal 10u peak floor at any budget. The driver
requires both `find_cut(graph)==saved_cut` and `check_cut(graph,saved_cut)==655360`.
This closes all infeasible smaller caps and makes the 29-point curve complete.
The favorable local terminal table at 9u has a finite state because its entry
is free; it is not used to prove this structural floor.

## Necessary first-final-GELU cut

Let t be the state immediately after the FIRST allocation of `b1_gelu`.
The frozen dependency closure contains exactly nodes 0..25. Thus the first
14 forwards of block 0 and first 12 of block 1 have happened, while block 1 DOWN
and RES2 are still unseen. No loss or backward can yet have happened. All
earlier repeated-forward work is nonnegative, so omitting it is favorable.
UP and GELU each own 4 units at t and immutable x owns 1. If the cap is C,
the earlier block's current owned live size r is at most C−9.

Let e be the state immediately BEFORE `b1_norm1` backward reads block 0's
output. The first block has no own backward before that read, by consumer
readiness. Define m as its minimum owned live units from t through e,
including e. Hence 0≤m≤r. The minimum is attained by some state in every
finite full trace. Block 0 holds at least m units through completion of the
last block's own backwards. The two blocks own disjoint tensor allocations
and repeated-forward costs.

The local problem charges a standing 1 unit input for global immutable x. A
block's own entry is freely and permanently available without any additional
allocation or owned work. This is favorable even if the real entry has been
dropped. No foreign block allocations are charged. Every inherited backward
read and dependency is preserved, with output allocation before drops.

Let D_C(L) be the exact local relaxation requiring a pending output read,
then all own backwards, starting with local live set L and all 14 first
forwards already seen. The earlier output may be consumed immediately once
available, then own backwards may start. This relaxes the real downstream
delay. Define A_C(r)=min D_C(L) over EXACT owned size r and E_C(m)=min A_C(q)
for q≤m. The earlier block's entire future owned work W0 obeys

    W0 ≥ max(D_C(L(t)), E_C(m)) ≥ max(A_C(r), E_C(m)).

The E term prices a suffix from a state attaining m. Taking max avoids
counting the same owned work twice. Current and minimum-state identities are
minimized independently; no free reachability between them is assumed.

The final block's terminal table allows all first12 repeats at full cost,
its first DOWN and first RES2 for free, arbitrary legal drops/forwards, then
an immediate favorable loss and all own backwards. A phase flag distinguishes
DOWN's first forward from repeats. Its initial live mask contains UP/GELU,
has DOWN absent, and owns at most C−1−r units. Earlier m units persist until
its norm1 backward, so its whole projection fits the favorable cap C−m.
Let Z_c(s) be the minimum terminal value over those masks of owned size≤s.
Every legal full trace therefore has additional work at least

    min over 0≤m≤r≤C−9:
        max(A_C(r), E_C(m)) + Z_(C−m)(C−1−r).

`factor_bound.py` computes this minimum by a one-stage min-plus state map;
a separate literal(r,m) enumerator checks every result. There is no finite
global operation horizon and no assumption of a fixed forward/backward order
beyond the frozen consumer readiness rules. All legal pre-cut repetitions,
prefetch identities, and delayed losses map to included favorable states.

All 14 owned local values total 22 units. Together with immutable x, every
local state and every allocation-before-drop forward transition already fits
by 23u. The terminal output allocation is included in that same full 14 set.
Consequently all three local transition graphs are exactly identical above
23u, and clipping local table requests at 23 is sound. The backward table
needs only first 12 owned values, totaling 20 units, and saturates at 21u.
Global C, r, and available-owned-size constraints retain the actual cap;
they are never clipped. A rehashed cap 22 as cap 23 demand-table forgery is
rejected, guarding the saturation boundary.

## Replay checks and scope

The inherited `ten-unit-proof` generators use reverse Dijkstra. Its separate
auditor enumerates forward legal moves and checks every Bellman inequality;
every finite table value must reach a correctly priced goal along tight
edges. Each of 45 tables is regenerated, hash-pinned, and fully audited.
Rehashed semantic forgeries include wrong graph fields, goal and other
prices, wrong cost units, illegal phase0 DOWN, capacity changes, and the false
saturation alias. The original PR10 witness retains its metadata; it checks
the 10u upper boundary and rejects four full-witness forgeries. All 19 possible
10u first-final-GELU live states independently reproduce the factor minimum.
Sixty-four synthetic summaries compare the two minimizers and reject three
invalid input classes. The joint replay verifies all29 complete schedules
and compares the actual endpoint minima and both owned-work components.

The result is a global fixed-cap work minimum when the necessary lower bound
equals the whole verifier-checked upper witness. Finite regional searches
used only for constructing those upper witnesses are not lower-bound
arguments. Unmatched results would fail this joint replay rather than become
an optimum claim. The new curve does not establish independent scientific
review or add fixed benchmark wins.

Credit: Doug Colkitt (@Mister-Meeseeks), the original graph/model/verifier and
trial contributors, the regional composition predecessor PR6, transformer
family PR10 (including its unchanged last-barrier classifier), exact local
PDB PR11, and the same author team's factored/common
region development. This is generated and checked by Codex, author-checked
only. Same-author-team cross-replays do not constitute independent human or
scientific validation.
