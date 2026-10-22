# Complete MLP work-memory curves

This source-only extension computes the entire fixed-memory minimum additional
forward-work function for both frozen MLP graphs. There are 29 integral caps
from 9 through 37 units for `mlp-b4`, and 65 caps from 9 through 73 for `mlp-b8`.
One unit is 4,096 bytes. The 94 prices contain 34 nondominated steps, stored
compactly in `EXPECTED.json`. These auxiliary curve points add no original
fixed benchmark wins. The parent's previously proposed b8 peak improvement
and its two cap-9 diagnostic certificates are not counted again.

From the repository root:

```sh
python3 -B research/mlp-frontier-round2/work-curve/replay.py --out SCRATCH
```

The module exports `run(repo,out)`, with `repo` pointing to the containing
checkout. It checks the pinned sources, expands the steps onto every integral
cap, reconstructs and verifies all 94 full schedules at budgets equal to their
exact work, and exhausts all 92 nonzero points at one less unit of work. It also
rechecks all ten original graph/budget points. Generated tables, measurement
logs and action lists stay under `--out`; no 94 saved schedules are committed.
Only the standard library and the parent's unchanged `chain_exact.py`, core
verifier and certificate constructor are needed.

The graph is a strict chain. First forwards therefore form a prefix, and
consumer readiness forces backward order. The parent proof explains why an
immediate loss, eager ready backwards, and dead suffix removal preserve some
schedule of no greater work or memory. The unchanged search then enumerates
every remaining individual drop and legal absent-output forward. Repeats pay
their full cost. Its absent-required-value work sum is admissible. The first
Dijkstra goal gives the minimum work at that cap; exhaustive failure at `W-1`
separately excludes every cheaper integral work value. A resource limit raises
and never supplies an exclusion. This is a finite computation with a reviewed
mathematical normalization argument, rather than a machine-checked proof.

The universal minimum peak is 9 units for each graph: immutable `x` occupies
one unit, and UP input and GELU output each occupy four during a mandatory
allocation-before-drop transition. Cap-9 positive schedules establish
attainability. The cap-8 diagnostic searches also exhaust, but the all-budget
floor follows directly from that mandatory coexistence, independently of any
chosen diagnostic budget.

The first zero-work caps are exactly 37 and 73. Before the terminal first
forward, loss has not occurred and no backward can have run. Every earlier
activation is a saved read of its immediate child's backward. Without repeats,
none may have dropped. The terminal output allocates alongside them before
loss, forcing the sum of all node allocations and immutable input. Retaining
everything realizes that sum. Larger caps have minimum work zero. All sizes
are multiples of 4,096, so byte caps between consecutive units have the same
feasible states. Together with the floor and zero tails, the integral sweep
therefore covers all byte caps.

Selected new auxiliary prices include b4 cap 12 at 4,292,608 work, and cap 17
at 2,195,456; b8 cap 11 at 21,364,736, cap 14 at 11,829,248, and cap 37 at
2,326,528. `COMPARISON.json` compares only the pre-round repository certificates
and the supplied PR6 package, with source hashes and no current outputs in the
historical input set. Its cap-9 improvements were already demonstrated in the
parent package. These comparisons are distinct from the exactness computation
and do not inflate the original fixed-case count.

Each search has a 250,000-state and 30-second limit. The complete replay has a
120-second aggregate guard. Two additional controls reject a changed frozen
graph and an unsupported saved requirement, so the specialized solver cannot
silently apply its chain theorem to that altered domain. The parent already
retains 800 randomized comparisons with an unnormalized oracle and other
semantic controls; this extension preserves those sources and evidence.

Credit Doug Colkitt (@Mister-Meeseeks) and the repository contributors for the
frozen model, graphs, verifier, trial mechanisms and baseline schedules; PR6 for
the regional predecessor; and this parent proposal for exact chain search and
its normalization proof. Codex AI for @0xqtpie authored the curve extension.
Evidence remains author-checked, including same-author-team implementation
review. Independent scientific review and maintainer acceptance are pending.
The results describe logical allocations and operation costs, not GPU memory
or training runtime.
