# Fixed13/14-unit minimum additional work: proof obligations and replay

This extension establishes two additional-forward-work minima for the frozen
transformer-b4-t128 graph when the full replay passes:

| Allocation cap | Bytes | Minimum additional work | Strict excluded budget |
|---|---:|---:|---:|
|13 units|1,703,936|421,494,784|421,494,783|
|14 units|1,835,008|355,270,656|355,270,655|

The original PR6 whole trace attains the13-unit value at its original
478,150,656 work budget and passes again at the exact421,494,784 budget.
The same author team's allocation-curve constructor supplies the copied
14-unit whole trace. Both complete traces pass the unchanged full verifier;
both native positive controls reconstruct another whole trace. A complete
replay must independently check the negative reduced graph before this is
an exactness result. A prepared native result alone is not that proof.

All model rules remain unchanged: immutable input is always resident, new
outputs allocate before drops, every first forward occurs before loss, the
sink is live at loss, and all consumer-ready backwards read their declared
values. Forward recomputations include every missing ancestor at full cost.

## Mandatory cut and exhaustive live-state cover

Choose the instant immediately after the FIRST allocation of final GELU.
Its ancestor closure is exactly the first54 nodes: three full14-node blocks
and the final block's first12. Final DOWN and RES2 have not yet happened,
so neither loss nor backward can have happened. The newly allocated GELU
and its required UP input are both live. They own8 allocation units and
immutable x owns1, leaving at most C-9 other units at cap C in {13,14}.

Exactly38 other seen values own1 unit each and14 own4 units each. At13 units,
every cut live set is one of the following83,007 possibilities:

    forced UP/GELU + a subset of at most4 of the38 unit values;
    forced UP/GELU + exactly one of the14 four-unit values.

The count is sum(k=0..4) choose(38,k)+14. At14 units, an optional four-unit
value may coexist with one optional unit value, so the complete count is
sum(k=0..5) choose(38,k)+14*(1+38)=585,481. No pair of four-unit optional
values can coexist in either case. This includes all earlier UP/GELU and
SCORES/PROBS values and the last block's SCORES/PROBS. DOWN/RES2 of the final
block are unseen and absent. The recipe does not price the prefix, enforce
which subsets can be retained by it, or impose a first-forward order on any
already seen node. These are favorable omissions. Any whole trace below its
case's claimed minimum supplies an included seed and affordable continuation.

Only two first forwards remain after the cut: DOWN then RES2. Their relative
order is forced by ancestry. Although the inherited native status string is
EXHAUSTED_FIXED_ORDER, its old-forward demand mode is0, allowing every useful
legal individual old forward after the cut and every consumer-ready backward.
Its encoded order among already seen nodes has no effect on what happened
before the cut. Thus the historical status name does not restrict global
first-forward orders in this necessary-tail reduction.

## Normalization and transitions

The parent package's arbitrary-drop oracle, eager backward normalization,
dead-future cleanup, and inclusion-minimal eviction reduction are reused.
They are not inferred from a search timeout or a heuristic order. Backwards
allocate nothing and have no adverse side effect, so ready backwards can be
eagerly executed. Values outside the ancestor closure of all remaining saved
reads can be dropped after loss. Before an allocation, arbitrary earlier
drops can be postponed until needed; a minimal sufficient subset of eligible
old live values then permits the same allocation. The existing size1/4
eviction enumerator covers every such subset, and output allocation remains
charged before any subsequent drop. New source does not alter these moves.

`replay.py` runs the parent's960 independently computed small explicit-state
oracle cases against this newly compiled executable. The source still reopens
states when a cheaper g is found; weight20 controls exploration order only.
It does not replace integer affordability checks or prove an exclusion.

## Nested current-identity bound

The full heuristic retains the parent's disjoint owned-cost/ancestor bounds.
The only stronger term changes the projected capacity of earlier owners.
At a state where the highest unfinished block is j, the guard requires all
earlier blocks'14 forwards seen and no earlier backward done; block j's first
12 seen; block j's norm1 backward unfinished; and either loss complete or
its final output still unseen. This ensures every earlier block still owes
its own future output read before any own backward.

For earlier owner i<j define e_i as the state immediately BEFORE norm1_(i+1)
backward reads its output. Set m_i to its minimum owned resident units from
the current state through e_i inclusive. The endpoint is before the read;
post-read drops cannot reduce this minimum. Let r_i be its current owned
units. Then0<=m_i<=r_i, and the actual vector has sum(m_i)<C because immutable
x stays live. Endpoints are ordered from later to earlier blocks by consumer
readiness.

Owner b's entire output-demand and backward projection completes by its own
norm1 read. Every earlier owner i<b therefore retains at least m_i units
through that whole projection. The favorable local capacity is

    c_b = max(9, C - sum(m_i for i<b)).

The floor9 increases capacity where a physical projected cap is below the
available table domain; it is a favorable relaxation, never an additional
restriction. The local standing1unit represents global immutable x. Its
actual block entry is always freely available without another allocation,
and all other foreign values are ignored.

Let D_c(L) be the exact all-seen local output-demand-then-backward table and
E_c(m)=min(D_c(L) : owned(L)<=m). At the current live identity L_b and at a
state attaining m_b, output demand and all own backwards remain pending.
If W_b is total remaining work owned by b, then

    W_b >= max(old_owned_bound_b, D_c_b(L_b), E_c_b(m_b)).

These are bounds on the same owned cost, so they are combined with max. A sum
would double-count. Distinct blocks' owned forward sets are disjoint and may
then be summed. If the active block j is after loss, its backward pattern
uses cap max(9,C-sum(all m)); before loss its phase-aware terminal pattern
uses that cap. The latter charges all old forwards, grants only first DOWN
and RES2 for free, and keeps their phase/history explicit. Already completed
later owners retain their original bounds. Taking max with the old total
keeps every inherited bound without counting any cost twice.

The native DP processes earlier blocks in ascending order. Its aggregate
state k is the sum of already chosen minima; the next D/E lookup therefore
uses max(9,C-k), and the next minimum ranges from0 through that owner's
actual current owned units. The independent checker instead enumerates the
Cartesian product of these minima. Every actual trace vector is included.
No identity is freely removed to satisfy a demand, and no ancestor replay
is silently omitted. Unreachable local tables discard only impossible
projections. All18 exact tables9..14 are independently Bellman/tight audited.

The new Cartesian reference matches native h on every state of both copied
whole witnesses from first final GELU onward, including pre-loss phases,
and never exceeds actual remaining work. The parent's240 seeded two/three
block explicit-state tests also exercise the endpoint theorem, saved reads,
different byte sizes, and unfinished backward prefixes. Those are meaningful
controls, not substitutes for the mathematical mapping or complete closure.

## Closed-label induction and positive boundary

The13-unit native run has83,007 seeds and exhausts172,238 distinct final
labels; the14-unit run has585,481 seeds and exhausts1,783 distinct final
labels. Both use the strict one-below work budget and complete without a
record/time limit. The explicit cap/budget pairs are the checker's complete
supported domain. A successful native run emits binary
little-endian uint64 triples(lp,done,g), with lp=live|(progress<<56). Neither
the saved hash nor native queue status is trusted as an exclusion. The
separately authored Python checker regenerates the full seed domain and
every reduced successor. Each affordable unpruned seed must have label<=0;
each affordable unpruned outgoing edge must have a target label no greater
than source g+edge cost. No affordable complete-backward goal can occur.
Induction then rules out every affordable normalized continuation. The
normalization mapping above transfers that fact to every full legal trace.

Generated binaries, inputs, tables and labels are not committed. Run
`python3 -B research/native-transformer-middle-proof-round2/work-optimum/replay.py
--out /path/to/writable/output` from the repository root. The standard-library
orchestrator builds C++17 source, audits tables, checks every label/edge,
reconstructs full positives, and rejects the negative controls. The
`--prepare-only` option deliberately returns PREPARED_NOT_CLOSURE_CHECKED;
that result does not establish either necessary-cut-domain exclusion.

EXPECTED
pins source, graph, original witness and all raw table values; a new replay
regenerates and semantically checks everything. Negative controls alter a
seed cost, omit a four-unit singleton, enable a restricted demand domain,
insert a goal, mutate bound bytes, redirect metadata, rehash semantic table
forgeries, underclaim whole work, omit a repeated forward, and reduce the
upper witness's budget by one. All must reject.

Credit: Doug Colkitt (@Mister-Meeseeks), the frozen graph/model/verifier and
trial contributors, PR6 retention transfer, the original transformer and
exact PDB work, and the parent PR13 normalization/closure machinery. Codex
generated and checked this extension. All reviews are within the same
author team; independent human or scientific validation is not claimed.
Native queue exhaustion alone is still not trusted as a scientific result.
The separately authored semantic checker and necessary-cut/normalization
mapping supply the exclusion argument. Public header comments clarify that
scope; EXPECTED records the previously replayed source hash and a hash of
the byte-identical program body after that comment-only cleanup.
