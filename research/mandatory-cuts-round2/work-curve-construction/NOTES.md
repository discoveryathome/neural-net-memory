# Constructive two-block work curve

This source-only replay reconstructs and verifies all 29 upper points for the
frozen `transformer-b2-t64` graph at caps 10 through 38 units of 65,536 bytes.
These are auxiliary Pareto research points, rather than 29 added original
benchmark cases. `EXPECTED.json` holds compact cap/work pairs. Action lists,
tables and measurement logs are regenerated under the chosen output directory.

From the repository root:

```sh
python3 -B research/mandatory-cuts-round2/work-curve-construction/replay.py --out SCRATCH
```

The module exports `run(repo,out,shared=None)`. The parent curve replay may pass
`shared=(bound_table_directory,bound_result)` to reuse audited backward tables.
Consumed binary hashes must match that result and canonical metadata. Frozen
node fields, input fields, capacity, layout and done masks are bound as well.
Standalone replay builds the same small backward tables. Both paths check every
full certificate with the unchanged verifier.

The constructor retains one earlier block output checkpoint and selects any
subset of its 12 useful saved-read ancestor values. Its first-forward retention
pass explicitly counts each output allocation before a following drop. If the
retained values occupy `r` units, the final region has local allowance `C-1-r`:
the checkpoint and retained cache remain outside that region, while the local
standing input represents global immutable `x`. The final allowance must be at
least 9 units. A complete 14-node regional search supplies its full training
plan. After that region finishes and drops its values, the earlier checkpoint
can drop and the earlier cache is completed using an exact backward table at
local cap `C`. Costs belong to disjoint blocks.

All 4,096 earlier cache masks are priced. For each mask, the program checks the
actual first-forward retention peak, the exact backward-table value, and the
last-region allowance. It then reconstructs one least-work schedule within this
class. The constructor itself makes no global work-optimum claim. Matching
necessary lower bounds live in the separate `work-curve-bound` proposal; the
joint replay must compare both sides before declaring equality.

The 14 local allocations total 22 units. Together with the standing immutable
input, every allocation target fits at 23 units, so larger local capacities
have the same action graph and may use cap 23. The 12-value backward closure
fits by 21 units. No capacity below 23 is aliased to 23. The final full-training
plan has zero extra work at 20 units and supplies larger final allowances.
Global `C`, the checkpoint, and the retained cache are always charged at their
actual sizes; saturation applies only to local lookups.

Every certificate is checked with its exact extra work as its budget. Caps
10, 13 and 19 are additionally checked against all four applicable original
fixed budgets. The cap-19 point costs 26,869,760; the older 26,804,224-work
certificate needs cap 20 and is not a cap-19 alternative. At cap 38 the new
schedule has exactly 28 first forwards and zero repeated work. Every generated
peak equals its stated cap.

Replay has a 120-second aggregate guard. Each backward-table build has a
200,000-state / 30-second limit. Full-region searches have at most 500,000
immutable records and 15 seconds each. Tight-edge reconstruction is capped at
200,000 states. Any limit raises and leaves the replay incomplete. Three
negative controls reject a changed frozen graph, a cap-23 table assigned to
cap 20, and an earlier checkpoint dropped before the next block's first read.

Only Python's standard library and this parent package's existing
`regional_exact.py`, `compose_schedule.py` and `ten-unit-proof/pattern_db.py`
are required. Their source hashes are pinned in `SOURCES.json`. There is no
runtime dependency on the separate four-block allocation proposal. Reused
retention and reconstruction logic is credited to that same-author-team work.

Credit Doug Colkitt (@Mister-Meeseeks) for the frozen model, graphs, verifier and
trial schedules; retention-transfer / PR6 and transformer-regions-round2 / PR10
for exact regional search and composition; and this parent proposal's PDB proof
for the backward tables. Codex AI for @0xqtpie authored this extension. Evidence
comes from one author team; scientific review and acceptance remain pending.
No GPU or training-runtime claim is made.
