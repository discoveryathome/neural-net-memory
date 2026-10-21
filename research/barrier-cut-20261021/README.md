# Proposed budget bounds for transformer-b4-t128

An author-checked mathematical proposal raises three working memory bounds from
1179648 to **1441792 bytes** at their fixed work budgets. At budget 956301312,
that matches Doug Colkitt's existing 11-chunk witness and proposes optimality.
The global charging argument still needs independent mathematical review.
`budget_cut.py` checks its finite structural lemma and arithmetic, and
`BUDGET-PROOF.md` gives the complete argument and its review obligations.

| Extra-forward budget | Working bound | Proposed bound | Existing witness |
|---:|---:|---:|---:|
| 239075328 |1179648 |1441792 |2883584 |
| 478150656 |1179648 |1441792 |1835008 |
| 956301312 (selected) |1179648 |1441792 |1441792 |

The related `../retention-transfer-20261021` package improves the actual 478150656
schedule to 1703936 bytes and 421494784 extra work. This bound package credits the
predecessor's unchanged high-budget witness. Neither package edits accepted or
working records, graph hashes, model semantics, or the core verifier.

## Universal floor and budget-sensitive extension

Let `u =131072` bytes. Allocating probabilities holds scores(4u), probabilities(4u)
and immutable x(u). Allocating GELU similarly holds UP(4u), GELU(4u), and x(u).
At a 9u cap either event fills memory. Take the last such event before block 0's
residual join. One necessary join input cannot be reached without another event
from that set. This proves the universal floor 10u =1310720 bytes, even with
unlimited recomputation. `reset_cut.py` reconstructs this last-barrier cut;
`cut.json` records its forced states and unrestricted forward closures.

At 10u, one extra unit tensor can survive a barrier. Enumerating all 820 relaxed
cases shows that every later block's output production has a last GELU allocation
whose only extra survivor is that block's residual1. Every earlier block tensor
is absent there. The charging proof uses three nested prefix replays and additional
attention/UP operations. With `F =119537664` and `C =8388608`, it proposes:

```
minimum extra work at peak <=10u: 6F +32C =985661440
```

Every fixed budget in the table is below that threshold. Whole-chunk allocations
then give a lower bound of 11u =1441792. The checker recomputes the survivor cases,
verifies the frozen graph and costs, and checks the arithmetic. The temporal
charging argument is author-reviewed mathematics, not proof-assistant validation.
Read `BUDGET-PROOF.md`, particularly its treatment of prefetch and disjoint charges,
before accepting the optimum proposal.

## Replay

From repository root, Python 3.9+ and standard library only:

```sh
python3 research/barrier-cut-20261021/verify_result.py
python3 -m unittest discover -s research/barrier-cut-20261021 -p 'test_*.py' -v
python3 research/barrier-cut-20261021/budget_cut.py benchmarks/graphs/transformer-b4-t128.json --check research/barrier-cut-20261021/budget-cut.json
python3 verify_all.py
```

Checks include wrong bound/count/survivor/hash/boolean rejection; the 820 survivor
cases; existing fixed-budget witnesses; the auxiliary 10u witness; and an exact
14-node regional control whose 10u minimum extra work is 85032960. The original
9u cut has 25 tiny-row controls and 146 small forward-pebbling differential cases,
26 of which admit the cut. These are all author checks.

## Construction attempts and pricing

The initial favorable loss relaxation priced mandatory first forwards, immutable
input, the sink, allocation transients, and at least each absent backward-required
value's own replay cost. At 10u it gave 209682432 extra work, which left the target
plausible. It relaxed dependencies and repeated evictions and was never a schedule.
Bounded forward/reverse beam searches and finite-slot integer repairs did not
produce a10u fixed-budget witness. Their limits did not establish impossibility.
The budget charging argument is separate evidence.

The auxiliary certificate uses 10u at its actual extra-work budget 1258192896,
exceeding the selected budget by 301891584. It demonstrates the universal floor
can be attained with more work and is consistent with the 985661440 lower bound.
It is not a schedule improvement on a fixed suite row. Original beam parameters
and outcomes remain in `TASK.json`; raw unsuccessful trajectories are local
session evidence. No solver-speed or hardware-memory comparison is claimed.

## Open next questions

Independently review the finite separator lemma and the global charging proof.
A legal 10u schedule below 985661440 extra work would refute the proposed bound.
For an actual schedule improvement, the remaining useful target is 12u at budget
478150656; the current new witness uses 13u. Global minimum work at 10u above the
threshold, formal proof translation, autograd saved-state fidelity, and native
Checkmate/DTR/Moccasin comparisons remain open.

Base: `a95cc1588fc57a07cfcf5a350206825e6f5b4b52`.
Seed: `dafc4be0863b7654352ffb2ba4a4d2df`. The original fidelity draw was released;
a documented numerical-track projection selected this graph/budget with the same
seed. The user later explicitly assigned the related fixed-budget schedule work.
`TASK.json` preserves that history. Codex AI agent for @0xqtpie authored this
package. Credit @Mister-Meeseeks for the model/verifier, trial schedules and prior
bounds, especially the 11u upper-bound witness. `SOURCES.json` pins predecessors.
This is a new result proposal for this graph, with extensive pebbling and
rematerialization prior art; it makes no external SOTA or total-training-memory claim.
