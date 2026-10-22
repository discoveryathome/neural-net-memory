# Exact additional work at the b2 ten-unit peak

For the frozen `transformer-b2-t64` graph at peak **655,360 bytes** (ten
allocation units), the minimum additional forward work is **106,725,376**.
The complete PR10 witness supplies the upper bound. An exhaustive necessary-cut
relaxation excludes budget 106,725,375. This settles additional work at this
fixed peak; it does not assert a new peak improvement.

From the repository root, standard-library Python:

```sh
python3 research/mandatory-cuts-round2/ten-unit-proof/replay.py --out /path/to/scratch
```

The replay regenerates all local tables, audits their forward edges and tight
paths, verifies the original complete witness, checks its tighter work budget,
runs forged-input controls, and exhausts the explicit preloss state graph.
No native binary, optional solver, omitted-prefix full certificate, or
precomputed binary table is required. Generated files stay under `--out`.

## Necessary first-GELU cut

Let one allocation unit be 65,536 bytes. Consider the allocation of the **first**
`b1_gelu` in any legal schedule. Its ancestor closure contains exactly the first
26 graph nodes. Consequently every block-zero first forward and the first
twelve block-one forwards have happened. The first block-one DOWN and RESIDUAL2
have not happened, because both depend on this GELU. No backward can have
happened, because all first forwards must precede loss.

The just-allocated GELU and its required UP coexist: four units each. The
immutable input occupies one unit. At the ten-unit peak, every other live
allocation therefore fits in at most one unit. Exactly eighteen of the seen
values are one-unit tensors. The initial domain contains their eighteen
singleton choices plus the empty choice, always alongside UP and GELU. The
two-unit attention values and other four-unit values cannot be present.

All work before this cut is discarded, giving every initial state cost zero.
The remainder of any legal global schedule maps to one of these nineteen
favorable states with no greater charged work. Arbitrary earlier recomputation
or first-forward ordering does not enlarge the domain: every ancestor has been
seen, and no descendant first forward can precede the cut.

## Explicit preloss closure

`micro_preloss.py` tracks the live allocation mask and whether the first final
DOWN has happened. It enumerates every individual legal drop and every legal
forward. The first DOWN and first RESIDUAL2 are free; all other forwards are
charged their frozen cost. The immutable input stays resident, and forward
output allocation is checked before any drop. There is no fixed old-forward
order, demand restriction, finite action horizon, eager-backward assumption,
or macro eviction rule.

At the first final RESIDUAL2, every graph first forward has happened and the
sink is live. Moving loss to this point is favorable: it only enables backward
earlier. Therefore the checker can stop at this boundary and test a necessary
lower bound on the remaining work, even if a source schedule delayed loss.

For each state, one minimum charged prefix cost is sufficient for its live
mask and phase; all other future semantics are identical. Every lower cost
label is processed. A candidate state is discarded only when its accumulated
cost plus the following admissible suffix bound exceeds the budget, or another
path already reaches the identical state more cheaply. Limits are explicit and
return `LIMIT`; they never establish exhaustion.

## Disjoint local continuation bounds

Each block's pattern problem makes its external entry permanently available
without allocating it. Its one fixed unit stands for the global immutable
input. All internal allocations still share at most the ten-unit cap. Ignoring
other blocks and a missing block-entry allocation makes these problems
favorable projections of every global continuation.

Block zero uses an output-demand table: its output must be available for the
future `b1_norm1` backward read before any block-zero backward is enabled. All
block-zero nodes have a path to its RESIDUAL2, whose backward waits for that
read. The local table allows the read immediately when its output is live and
then permits local backwards, relaxing the actual delay.

Block one uses a terminal-phase table until its first RESIDUAL2. All twelve
pattern-needed values have already been seen, and no local backward has run.
The table keeps the two remaining first forwards free and all other forwards
charged, enforces their allocations, then enters the local backward problem.
After the first RESIDUAL2 boundary, the ordinary backward table supplies its
remaining owned-work bound.

The two terms charge disjoint sets of fourteen node-forward operations. Their
sum therefore lower-bounds global remaining additional work; memory estimates
are not added. The exact full graph hash, every local node field, input/output
mapping, saved reads, units, phases and table layouts are checked. The separate
auditor enumerates forward transitions, checks Bellman's inequality, and proves
every finite table value has a tight path to a correctly priced goal. It also
checks impossible states and all goal values. This validates both finite values
and unreachable markers independently of reverse-Dijkstra construction.

## Results and controls

At budget **106,725,375**, the explicit graph exhausts **2,463 states** and
**16,754 drop/forward edges**. No loss boundary survives. At budget
**106,725,376**, a boundary remains with prefix cost 21,315,584 plus local
suffix bound 85,409,792. This positive boundary is a relaxation control; the
separately verified complete PR10 witness establishes actual attainability.

The saved witness retains its original metadata and 110,821,376 challenge
budget byte-for-byte. Replay also verifies the same actions with the tighter
106,725,376 budget. Across 23 actual preloss boundaries, both local prices are
checked against actual future charged work of their own block (46 comparisons).

`high-budget-reuse.json` contains those same actions with the original highest
challenge budget221,642,752. At its unchanged655,360-byte peak this reduces
work from the strongest pre-round213,614,592 certificate to106,725,376,
or50.04%. Replay checks the action equality and this budget explicitly. This
is reuse of the PR10 construction, not another independent schedule discovery.

Nine rehashed table forgeries test goal overclaim, underclaim, frozen local
costs, full graph identity, cost units, phase legality and cap consistency.
Separate full-witness mutations test a changed graph cost, underclaimed work,
one-below budget and an omitted regeneration. Table binary hashes and exact
positive/negative outcomes are pinned by `EXPECTED.json`; the parent package's
source manifest pins this subtree. `RESULTS.json` is generated in scratch.

## Provenance and limits

Base `a95cc1588fc57a07cfcf5a350206825e6f5b4b52`; master seed
`dafc4be0863b7654352ffb2ba4a4d2df` (this proof replay is deterministic).
Explicit parent-authorized secondary-work research followed the broad user
assignment. Credit Doug Colkitt (@Mister-Meeseeks) for the frozen model,
verifier and predecessor schedules; PR6 for regional composition; PR10 for the
upper-bound witness; and the same-session local-pattern work for the three
generators and separately authored Bellman auditors. Codex AI for @0xqtpie
authored this follow-up. Evidence is author-checked only; same-author-team
checks do not constitute independent scientific validation.

Core verifier, graph, model, and accepted/working records are unchanged. No GPU
runtime or external solver comparison is claimed. The local table generators
are reusable code; the nineteen-seed theorem is pinned to this exact graph,
cut and cap. Research and audit limits do not support conclusions when reached.
