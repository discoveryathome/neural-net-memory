# Less recomputation and the complete two-block transformer frontier

For the unchanged `transformer-b2-t64` graph, a new schedule at **851,968
bytes** reduces additional forward work from **54,198,272 to 52,035,584
(3.99%)**. It retains block0's residual1 while training block1, then reuses
that checkpoint for block0 backward. The full certificate passes the unchanged
verifier at the original 55,410,688 budget.

All three nonzero fixed peak levels now have matching minimum-recomputation
bounds:

| Peak bytes | Exact minimum extra work | Excluded work budget | Schedule source |
|---:|---:|---:|---|
|1,245,184|26,869,760|26,869,759|PR10 regional construction|
|851,968|52,035,584|52,035,583|new retained-residual1 construction|
|655,360|106,725,376|106,725,375|PR10 ten-unit construction|

At the already known655,360-byte minimum peak, the ten-unit trace also fits the original highest budget221,642,752 and cuts the strongest pre-round work213,614,592 by50.04%. That is reuse of the PR10 witness, explicitly retagged and replayed; it is not counted as another independent construction.

These are exact secondary-work optima at fixed peaks. The new result improves
recomputation; it adds no peak reduction. The construction was priced against
the necessary event relaxation first, then 111 feasible cache sets were scored
using exact local pattern costs. The winning full trace matches the global
relaxation. Its regional method comes from PR10; the certificate is
self-contained and no other PR is required for replay.

The [complete work-curve extension](work-curve-bound/README.md) now supplies
matching global bounds and full legal schedules at every integral cap from
10 through38 allocation units: **29 exact Pareto points**. Its first zero-work
peak is2,490,368 bytes (38 units). A copied, credited PR10 structural classifier
excludes every cap below10 units at any work budget. Every tensor size is an
integral65,536-byte unit, so the curve also covers intermediate byte allowances.
The new [constructor](work-curve-construction/NOTES.md) regenerates all29 full
traces at their exact work budgets and additionally checks the four original
nonzero challenge budgets. The intermediate points expand coverage rather than
adding original benchmark wins.

The necessary curve proof gives all work before first final GELU free. Its
earlier region owns a current-size/future-minimum pair(r,m); the minimum persists
until the downstream output read and reserves those bytes from the final local
region. Exact audited output-demand and terminal prices minimize over every
such pair. Matching full schedules prove attainability. All45 local tables
are regenerated and audited over12,856,059 transitions, with semantic table
forgeries, direct algebra checks and actual per-owner trace controls.

The results include arbitrary recomputation before loss and arbitrary backward
orders. Frozen graphs, model, verifier, and accepted/working records are unchanged.
Evidence is author-checked within one AI-assisted author team; outside scientific
review and acceptance are pending.

The first two exclusions use OR-Tools 9.15.6755, one worker, random seed 20261021,
30 seconds and 300MB per solve. The original session used an external 350MiB
RSS guard. Exact integer INFEASIBLE statuses one work unit below each
construction supply the exclusions; matching OPTIMAL relaxations, full
verifier replay, and actual-trace mappings are positive controls. No incomplete
optimization bound is used as an exclusion. The third exclusion is a small
explicit preloss closure with audited local pattern databases; it requires only
the standard library and no optimizer.

## Necessary relaxation and proof

Select each block's ancestor spine:
norm1, scores, probs, context, proj, residual1, norm2, up, gelu, down, residual2.
Take their first-forward events, loss, and their backward events in reverse.
These events occur in that order in every legal trace: each forward pivot is an
ancestor of the next, all first forwards precede loss, and backward completion is
consumer-ready. After each scores backward, add the first backward of its q/k
pair. Both depend on the preceding norm1 pivot, both feed scores, and both
require norm1. Thus this extra cut is strictly between scores backward and norm1
backward, with norm1 forced live. The code checks those ordering preconditions.
There are 47 cuts for this fixed graph.

At first-forward cut t, let S_t be its ancestor closure including itself. At
loss/backward cuts let S_t contain all nodes. These sets are ancestor-closed and
monotone. L_t is the actual live set intersected with S_t; force the event's
output/dependencies, sinks, or saved reads. Charge every immutable input at every
cut, and constrain total live bytes by the cap.

For the disjoint interval between consecutive cuts, R_t contains each old node
in S_t that is forwarded at least once during that interval. Every such forward
is a charged repeat. A next-cut old live value was retained or repeated:
L_next(i) <= L_prev(i)+R(i). When R(i) is true, each old dependency was already
live or also repeated in the interval. Ancestor closure makes that dependency
old too. Non-recomputable nodes have R=0. Charge each R once. This undercounts
multiple repeats and ignores all unselected time intervals, so its work is no
greater than real additional work.

**Prefetch correction:** a node newly appearing in S_next may already have
executed on a parallel branch before cut t. Imposing old dependency availability
for every such node is unsound. Only impose it if the node descends from the
preceding first-forward pivot, guaranteeing a first execution after that pivot.
The explicit cap 9 zero-work parallel-V fixture is accepted by the corrected
model and rejected by the deliberately naive rule. This correction is essential.

Finally P(i)=L_prev(i) AND L_next(i) AND NOT R(i) is continuously resident: a
drop would require a repeated forward to restore it. During every selected old
regeneration and every guaranteed-new first forward, the union of all P values,
that operation's distinct dependencies and its newly allocated output must fit
beside immutable inputs. The conditional linear constraint uses a sufficient
integer big-M; P is a subset of an endpoint live set. It counts allocation before
drops. Paying an unnecessary R to avoid P only enlarges the relaxed domain.

Any legal trace therefore maps to a feasible integer assignment with no greater
charged work. Solver infeasibility at the stated cap/budget excludes every real
trace there. A feasible L/R policy alone is not a schedule.

## Replay and controls

For the ten-unit point, the first final GELU forces UP and GELU beside the
immutable input, leaving at most one allocation unit among eighteen small seen
values. The nineteen favorable initial states receive all previous work free.
Every legal individual drop and repeat forward is enumerated until first final
RESIDUAL2; its two outstanding first forwards remain free. Disjoint block-owned
output-demand and backward bounds price the remainder. At work106,725,375 the
closure exhausts2,463 states and16,754 edges with no surviving loss boundary.
The matching full PR10 trace establishes attainability. See
[the complete cut argument](ten-unit-proof/README.md).

The local generators and separately authored Bellman/tight-path auditors check
351,700 edges, nine rehashed table forgeries, four full-witness mutations and
46 actual-state owned-work comparisons. Every second-block local node field
is checked against the first-block template before using its prices.

Use Python3.12 with the pinned optional dependency already available:

```sh
python3.12 -B research/mandatory-cuts-round2/replay.py
python3.12 -B -m unittest discover -s research/mandatory-cuts-round2 -p 'test_*.py' -v
```

The replay checks source/input hashes, the unchanged full schedule verifier,
actual-trace mappings and all three exact positive/negative boundaries. It runs
the standard-library ten-unit subtree in a separate process. That subtree can
also be replayed alone without OR-Tools.
The tests compare the relaxation and mappings against120 tiny exact optimum
traces, with branches, self/ancestor/empty saved reads, nonuniform sizes/costs,
non-recomputable nodes, and the explicit prefetch falsifier.

Sources and graph hashes are pinned in SOURCES.json; command receipts are in
VERIFY.md and RESULTS.json. Replays need no network or credentials. No hardware
memory or elapsed-training speedup is asserted.

## Credit and status

Discovery@Home and the problem formulation: Doug Colkitt / @Mister-Meeseeks.
The 1,245,184-byte positive trace comes from PR10 transformer-regions round2 research,
using the trial's certificate/verifier conventions and the prior PR6 regional
exact solver. The present necessary-event/persistence formulation and correction
were developed in this round; the tiny chain fixture generator is adapted from
the parallel ResNet package. Codex AI authored this package and the author team
checked it. Same-team code/mapping checks are not independent scientific review,
maintainer acceptance, or accepted frontier records.

The new 851,968-byte trace was constructed by the parent Codex agent using the
same regional machinery, with block0 residual1 retained. Credit PR11 for the
local backward-pattern implementation used during cache pricing, PR10 for the
ten-unit positive trace, and the same-session PDB work for its generators and
separately authored auditors. The ten-unit exclusion was reviewed by another
agent on this author team; that is not outside scientific review. Larger-graph
work optima remain a separate research question.
