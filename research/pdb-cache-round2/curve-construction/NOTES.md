# Constructive higher-memory work curve

This source-only replay constructs and checks 69 full schedules for frozen
`transformer-b4-t128`, at caps 14 through 82 units of 131,072 bytes. These are
auxiliary Pareto points between the original benchmark rows. They are not69
additional original-case wins. `EXPECTED.json` stores compact cap/work pairs;
all action lists are regenerated under the explicit output directory.

From the repository root:

```sh
python3 -B research/pdb-cache-round2/curve-construction/replay.py --out SCRATCH
```

The module exports `run(repo,out,shared=None)`. A parent replay may pass
`shared=(factored_table_directory,factored_result)` to reuse its audited
backward tables. Every consumed raw hash is checked against that result and
its metadata; local frozen nodes, inputs, capacity, layout and done masks are
also bound. Standalone replay builds its own small backward tables. Every
upper point is checked by the unchanged full verifier in both modes.

The constructor jointly selects one retained mask from the 12-value saved-read
ancestor closure in each earlier block. It charges output checkpoints outside
the local problem. For current block `b` and earlier retained size `k`, the
local cap is `C-b-k`. A concrete first-forward retention pass must fit that same
cap. After later regions complete and drop their values, the exact backward
table prices this block from its chosen mask.

For each local cap and mask size, only the cheapest feasible mask is needed:
later regions depend on that size, rather than the mask identity. A three-layer
DP keeps the least earlier sum for each total retained size. It then adds an
exact full-training price for the final block at `C-3-k`. The priced class
requires this final cap to be at least 10; it includes no restriction on the
last block's first-forward ordering because its complete 14-node Dijkstra is
unreduced. Earlier passes retain the stated fixed order and output checkpoints.
This constructor alone makes no global work-optimum claim.

All 14 local node allocations total 26 units, plus the standing immutable input.
Thus every local allocation-before-drop target fits by 27 units. Larger-cap
backward tables have exactly the same action graph and may alias cap 27. The
12-value backward closure itself fits by 25. The full-training plan has zero
extra work at 22, so the same plan supplies every larger last-block allowance.
No cap below 27 is aliased to 27. The global DP retains its original cap and all
outside allocations; only local table lookup saturates.

Replay reruns the 13 exact full-training prices at caps 10–22. Each query has
at most 500,000 immutable records and 15 seconds; backward-table queries have
at most 200,000 states and 30 seconds. The complete pricing/construction run has
a 120-second aggregate guard. Limits raise and never establish a completed
price. Tight-edge reconstruction has its own 200,000-state bound.

All 69 full certificates use a budget equal to their exact claimed extra work.
The 22/36-unit traces are additionally checked at their original fixed budgets.
At 82 units there are exactly 56 forwards and zero repeats. All verified peaks
equal their stated caps. Three negative controls reject a changed frozen graph,
an oversized local table assigned below the alias threshold, and a checkpoint
dropped before the following block's first input read.

The separate `curve-bound` work can establish matching lower bounds. A parent
comparison is required before labeling any upper point globally optimal.
Unmatched points remain verified upper bounds. Core semantics, accepted records
and the frozen earlier allocation/factored proof files are unchanged.

Credit Doug Colkitt (@Mister-Meeseeks) for the model, graph, verifier and trial
schedules; retention-transfer / PR6 and transformer-regions-round2 / PR10 for
regional exact search and composition; and the same-session PDB/allocation
work for reused public helpers. Codex AI for @0xqtpie authored this extension.
Evidence remains from one author team, with scientific review and acceptance
pending. No GPU or training-runtime claim is made.
