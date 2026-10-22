# Verification receipt

All prototype/test Python was executed with the unchanged session profile:

```sh
sandbox-exec -f "$S/research.sb" /opt/homebrew/bin/python3.12 -B \
  "$S/interval-proof/research/mandatory-cuts-round2/replay.py"
sandbox-exec -f "$S/research.sb" /opt/homebrew/bin/python3.12 -B \
  -m unittest discover -s "$S/interval-proof/research/mandatory-cuts-round2" -p 'test_*.py' -v
```

The session's preinstalled dependency directory was on PYTHONPATH. No install,
network, credential access, core/model changes, or accepted-record changes were
made. Replays verify the full positive trace with unchanged verifier.py.

The initial exploratory boundary calls used the exact same formulation and
positive witness. Positive OPTIMAL26,869,760 in2.98s, negative INFEASIBLE budget
26,869,759 in3.12s, with139,072/139,536KiB RSS respectively, below350MiB guard.
Portable package replay and tiny controls are recorded in the adjacent logs.
Raw best-bound diagnostics are not used as an infeasibility certificate.

Disabling persistent allocation constraints was also tried at the same negative
budget with a5s limit. It returned UNKNOWN; this is an inconclusive ablation,
not evidence that persistence is necessary or that the relaxed target is feasible.

The prefetch test intentionally confirms a rejected naive formulation. It
demonstrates why the corrected descendant test is needed. Broader unfinished
large-graph research was excluded from this focused package.

The later middle-peak extension prices a new 851,968-byte schedule at52,035,584 work against the same necessary relaxation. Its one-unit-below exclusion is INFEASIBLE; a matching legal schedule and exact positive optimization are replayed alongside the original case. The extension adds no solver/model change. See replay-two-points.log and RESULTS.json for final portable boundary statuses.

The final extension adds the655,360-byte point with exact work106,725,376.
The standard-library ten-unit subtree regenerates and audits three local
tables, checks all local node projections and the original PR10 full trace,
then exhausts the necessary preloss closure at work106,725,375. Its positive
relaxation boundary is a control; the full unchanged verifier establishes
attainability. A separate author-team agent reviewed the cut and replay.

The final combined replay reports all three exact work levels. No native binary
or generated binary table is committed. Source pins include the complete new
subtree; generated scratch output is removed after each combined replay.

The complete work-curve extension regenerates45 local tables, audits12,856,059
forward transitions, checks semantic forgeries, and reconstructs29 full traces
at exact work budgets. Its copied PR10 last-barrier classifier supplies the
universal10-unit peak floor; the positive zero-work38-unit trace and positive
37-unit lower price complete the upper endpoint. Four original nonzero
challenge budgets are additionally replayed. The original highest-budget
ten-unit reuse reduces213,614,592 to106,725,376 work (50.04%) with identical
PR10 actions, explicitly checked in `ten-unit-proof/high-budget-reuse.json`.

One parent combined-record invocation omitted the already installed optional
solver directory from PYTHONPATH and failed at import before executing research.
It was corrected and rerun; that setup failure supplies no scientific result.
