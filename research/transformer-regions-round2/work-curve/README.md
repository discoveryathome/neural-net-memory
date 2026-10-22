# Complete one-block transformer work curve

The unchanged `transformer-b1-t32` graph has eleven nondominated memory/work
points. At caps of9 through19 allocation units (32,768 bytes each), exact
minimum additional forward work is:

| Cap units | Extra work |
|---:|---:|
|9|23,281,664|
|10|15,851,520|
|11|7,725,056|
|12|5,627,904|
|13|3,530,752|
|14|1,433,600|
|15|868,352|
|16|344,064|
|17|81,920|
|18|40,960|
|19|0|

For every nonzero point, replay constructs and checks a full schedule, then
exhausts the same complete state graph with one less work unit. The inherited
raw Dijkstra tracks `(live, seen, backward-done, loss)` and every individual
legal forward, drop, loss and backward action. It imposes no first-forward
ordering, eager-backward rule or demand normalization. All allocations are
checked before drops. Limits raise and never establish an optimum.

All graph sizes are integral allocation units, so intermediate byte caps admit
the same states as the next lower integral cap. Below9 units, the required
first GELU and its UP dependency occupy8 units beside the immutable input;
the replay checks those graph fields. At19 units the full verified schedule
uses zero additional work, which is the universal work floor. These facts and
the eleven exact prices cover every memory allowance.

Run `python3 research/transformer-regions-round2/work-curve/replay.py --out SCRATCH`
from the repository root. It uses the standard library, at most500,000 immutable
records and15 seconds per local query; generated full certificates stay under
the explicit scratch directory. The package replay invokes it with a temporary
directory during `--reconstruct`.

The9-unit point is the same6.33% secondary improvement reported by the parent
package. The remaining points expand coverage between the original fixed
budgets; they are not additional wins on those benchmark cases. The first
220,000-record scan reached its cap at13 units; the single bounded pivot to
500,000 completed every point (largest positive state map281,097). Evidence is
author-checked within the same AI author team; outside scientific review and
acceptance remain pending. No GPU or training-runtime claim is made.

Base `a95cc1588fc57a07cfcf5a350206825e6f5b4b52`; seed
`dafc4be0863b7654352ffb2ba4a4d2df`. Credit Doug Colkitt / @Mister-Meeseeks for
the frozen graph, model, verifier and trial schedules, PR6 for the exact regional
solver, and the parent PR10 work for its full-state extension. Codex AI for
@0xqtpie authored this curve replay. No frozen semantics or accepted records
are changed.
