# Less recomputation and an exact high-memory transformer frontier

For the frozen `transformer-b4-t128` case with additional-forward budget
956,301,312, a new full schedule reduces additional forward work from
**737,935,360 to 702,349,312** at the existing **1,441,792-byte peak**.
Two further full schedules improve work at higher existing peaks:

| Peak bytes | Original budget | Strongest previous work | New work | Reduction |
|---:|---:|---:|---:|---:|
|1,441,792|956,301,312|737,935,360|702,349,312|4.82%|
|2,883,584|239,075,328|234,717,184|234,618,880|0.0419%|
|4,718,592|119,537,664|117,211,136|117,178,368|0.0280%|

The latter two now have matching global minimum-work bounds. A broader source-only
replay reconstructs69 full schedules and gives matching bounds at every cap from
15 through82 allocation units: **68 exact work optima**. These intermediate
Pareto points expand coverage; they are not additional original benchmark wins.
The unchanged full verifier checks every allocation and every repeated forward.
The1,441,792-byte point remains a constructive work gain with no global
minimum-work claim. None of these results reduces an original peak further.

## Constructor and replay

From the repository root, standard-library Python 3.9 or later:

```sh
python3 research/pdb-cache-round2/replay.py
python3 -m unittest discover -s research/pdb-cache-round2 -p 'test_*.py' -v
python3 research/pdb-cache-round2/controls.py
python3 verify_all.py
```

The replay checks pinned sources, verifies the saved complete certificate, builds
the tiny local tables, reconstructs the exact action list and verifies it again.
It also replays the joint cache-allocation constructor and the complete high-memory
curve with all local Bellman/tight-path audits and positive/negative controls.
No optional solver, precomputed binary table, omitted-prefix initialization or
external package is needed. The certificate can also be passed directly to
`verifier.py` with budget 956301312.

`cache_policy.construct(graph)` returns the complete action list. The constructor
is deliberately limited to the frozen b4 graph and allocation caps nine through
thirteen units. A failed heuristic run makes no infeasibility claim. Every first
forward, the loss barrier and all backwards are present. The immutable input is
always resident; a new output fits before dependent inputs can be dropped.

## Eviction mechanism

For each possible eviction, the constructor measures the increase in a local
pattern database's remaining work after deleting that value. The local backward
table tracks consumer readiness and saved reads. An earlier block's output-demand
table also includes its future output read. Each table makes its block input
permanently available, so it provides an optimistic local price. These values are
used only to choose evictions; schedule legality comes from the full verifier.
During the first pass they are a prediction of later reuse, not a proved bound
on that partial first pass.

The eviction score divides the marginal price by tensor bytes and the distance
to its next direct request, raised to 0.85. A factor of 3.2 favors three keepers:
`b0_residual1`, `b1_residual2`, and `b3_residual1`. Values with no remaining use
are dropped first. First-forward V placement is delayed until after PROBS in
blocks zero and three, and follows K in blocks one and two. Backwards use the
reverse of the delayed-V topological order. All orders are checked in the final
full trace.

The winning policy came from a bounded refinement: 10,000 attempted mutations,
7,590 distinct parameter sets, 6,583 completed constructions, 53.79 seconds and
master seed `dafc4be0863b7654352ffb2ba4a4d2df`. The refinement RNG uses
its first 64 bits, hexadecimal `dafc4be0863b7654`; the earlier grid shuffle
uses integer seed 20261021. An earlier 720-policy grid found a
smaller gain; optional-slot deletion further refined that earlier witness.
The unsimplified winning trace's deletion-only and immediate-dependency slot
domains could not improve that trace. Those finite-domain negatives are not global impossibility results.
`EXPERIMENTS.json` preserves counts, parameters, resource limits, source hashes
and outcomes; the full raw session logs remain in the session research scratch.
The portable contract here is exact reconstruction of the winning schedule.

## Joint allocation and necessary regional prices

The [allocation extension](allocation/NOTES.md) prices all4096 useful earlier
cache masks and allocates their bytes jointly across three earlier blocks. Each
full schedule charges every external checkpoint while an exact local region
trains. It produces the two higher-memory gains above. The
[generalized constructor](curve-construction/NOTES.md) reconstructs every full
trace at caps14 through82, checks its exact work budget, and additionally checks
the original22/36-unit challenge budgets. No action lists or generated binary
tables for the entire curve are committed.

The [factored mandatory-cut proof](factored-bound/README.md) starts at first
final GELU, gives all earlier work free, and prices disjoint block-owned future
work. A region's minimum occupancy persists until a required downstream output
read, reserving that many bytes while later regions train. Exact local
output-demand and terminal databases supply favorable prices; a small integer
DP minimizes over every necessary current-size/minimum-size tuple. A separately
authored direct enumeration checks the factoring. The
[nested endpoint extension](curve-bound/NESTED-PROOF.md) uses each region's own
output-read endpoint and closes one additional cap. It preserves arbitrary
first-forward, recomputation and backward orders.

The [joint curve replay](curve-bound/README.md) audits all consumed local tables
and verifies every generated full schedule. Caps15 through82 match; at14 units
the remaining lower/upper gap is819,200 work units. The first zero-work peak is
82 units (10,747,904 bytes), with a positive lower bound at81. All graph sizes
are integral131,072-byte units, so these prices cover the intermediate byte
allowances too. The fully audited unreachable terminal problem at9 units also
gives a universal10-unit peak floor at any work budget.

## Controls and limits

Five tests cover reconstruction, full verification, charged work limits, frozen
graph and parameter validation, and rejection of an omitted regeneration.
`controls.py` replaces only the eviction price while holding the winning
parameters fixed. Ancestor recovery and zero marginal prices produce
1,517,387,776 and 4,557,045,760 extra work respectively. Both fail the original
budget. These are untuned mechanism controls, not a fair comparison between
retuned solvers, and not evidence of external state of the art.

The minimum work at the1,441,792-byte peak remains open. Other keeper policies,
lookahead and joint retention transfers may improve it. This proposal does not
measure GPU memory, runtime, exporter fidelity or external solver performance.
Core code, graph/model semantics, original and working frontier records remain
unchanged. Independent scientific review and maintainer acceptance are pending.

## Provenance

Base `a95cc1588fc57a07cfcf5a350206825e6f5b4b52`; explicit user-assigned broad
frontier research and secondary schedule refinement. `TASK.json`, `SOURCES.json`
and `VERIFY.json` record the pinned task, inputs, implementation and replay.

Codex AI agent for @0xqtpie authored this follow-up. Credit **Doug Colkitt
(@Mister-Meeseeks)** for the model, frozen verifier, predecessor schedules and
trial Cache; prior PR6 for regional composition; and the same-session native
proof/PDB work for `pattern_db.py` and `output_demand_db.py`, copied here with
only their repository import path adapted. Results are author-checked only;
same-author-team checks do not constitute independent scientific review.
Code and project text retain the repository's MIT license.

The separate same-author-team proof in [PR #13](https://github.com/discoveryathome/neural-net-memory/pull/13)
closes the work minima at 13 and 14 units using checked finite cut closures.
Together, the two packages propose 70 exact work prices at caps 13 through 82.
This package's own factor bound at 14 remains 819,200 below its upper witness;
its 68 matching prices and generated RESULTS are unchanged. The remaining global
work-minimum questions are caps 10, 11 and 12. This cross-reference adds no runtime
dependency and supplies no independent scientific review.
