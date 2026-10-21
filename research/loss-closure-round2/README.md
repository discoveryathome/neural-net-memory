# Mandatory-event dependency closure strengthens eleven bounds

This package proposes stronger lower bounds on eleven fixed graph/budget rows.
It exhausts a **necessary relaxation of every legal schedule**, using only
standard-library integer dynamic programming. It does not construct a schedule.
A bound matching a legal witness proposes that row's optimum. All evidence is author-checked;
independent scientific review and maintainer acceptance remain open.

| Graph | Budget | Working bound | Dependency-closure bound |
|---|---:|---:|---:|
| transformer-b1-t32 |6653952 |294912 |393216 |
| transformer-b2-t64 |27705344 |720896 |1245184 |
| transformer-b2-t64 |55410688 |589824 |851968 |
| transformer-b4-t128 |119537664 |2752512 |4718592 |
| transformer-b4-t128 |239075328 |1179648 |2883584 |
| resnet-b4-c32 |75694080 |1048576 |2097152 |
| resnet-b4-c32 |151388160 |1048576 |1572864 |
| mlp-b4 |2129920 |69632 |86016 |
| mlp-b4 |4259840 |36864 |53248 |
| mlp-b8 |4259840 |118784 |135168 |
| mlp-b8 |8519680 |53248 |69632 |

Ten bounds match existing working witnesses. The remaining b2 low-budget bound
matches the parallel transformer's new 1245184-byte witness. The accompanying
ResNet package additionally settles its high nonzero budget and full staircase.
These bounds provide simpler complementary controls. The prior
PR #6 11-chunk transformer proposal concerns other budgets and a different proof.
No graph, model, verifier or accepted/working result record is modified.

## Why the bound applies to every schedule

Take any legal complete action trace and inspect its loss barrier. Let `L` be
the internal values live there. Immutable inputs remain live by the model, and
every sink belongs to `L`. Let `R` be all internal values absent at loss but
executed again after loss. Ignore any later executions of values already in `L`.
The sets `L` and `R` are disjoint.

Every value required by a backward belongs to `L union R`: otherwise that
backward cannot read it. Every internal dependency of a value in `R` also belongs
to `L union R`: if absent at loss, it must execute again before supplying the
later forward. No non-recomputable node belongs to `R`. Each member of `R` costs
at least one repeated forward, so `sum(cost(R)) <= B`. Repeats before loss and
multiple repeats afterwards only increase actual work and are safely relaxed.
Loss memory is exactly fixed input bytes plus `sum(bytes(L))`.

Minimizing this memory over **all** disjoint sets satisfying those necessary
conditions gives a lower bound on loss memory, hence on peak. The relaxation
ignores forward/backward ordering, repeated eviction, allocation transients and
simultaneous post-loss memory. Its minimizing sets are not legal schedules.
The usual largest local-allocation bound can be combined by taking the maximum.

## Mandatory first-forward events

At the allocation boundary of the first forward of a pivot `v`, every ancestor
of `v`, including `v`, has executed. Write this ancestor-closed set `S`. No
backward has executed: all first forwards precede loss. Every globally
backward-required value in `S` therefore has a pending read. If absent, it must
execute again later. Its regeneration dependencies also lie in `S`. The pivot's
output and inputs coexist, alongside all immutable external inputs.

Apply the same necessary retained/regenerated conditions to `S`, forcing the
pivot and its internal dependencies retained. Ignore all outside-`S` allocations:
they cannot generate an ancestor in `S`, so ignoring their memory and work is
safe. Each member of `R` was already seen and costs at least one repeat. Work
spent before this cut is also ignored. These are favorable relaxations valid
for arbitrary prefetch, retention and backward ordering. Taking the maximum of
loss and every first-forward bound gives a valid peak bound.

`cut_frontiers` forms an internal ancestor-induced graph to reuse the enumerator.
Its pivot saved-read list encodes **all original pending requirements in S**;
`forced_live` encodes output/input coexistence. This is relaxation bookkeeping,
not an altered benchmark or a candidate schedule. `lower_bound` rejects query
budgets above the frontier's construction ceiling: a truncated frontier cannot
justify a larger-budget bound.

## Exact finite dynamic program

Each operation has three choices: retained at loss (`L`), regenerated (`R`), or
neither. Sinks must be retained. Backward-required values cannot choose neither.
An `R` choice requires each internal dependency to have chosen `L` or `R`.
External dependencies are always available. `R` is forbidden for a node marked
non-recomputable. These choices enumerate the entire necessary relaxation,
without an event horizon, supplied trace or fixed backward order.

Scan the already validated topological serialization. A bit mask records which
previously assigned nodes chose `L` or `R`, restricted to nodes with future
forward consumers. Once a node has no unprocessed forward consumer, its bit is
forgotten; no subsequent condition depends on it. Retained bytes and repeated
work remain accumulated even after the bit is forgotten. No memory is freed
by that bookkeeping step.

For an equal mask keep only Pareto labels `(retained bytes, work)`. A label with
no smaller memory and no smaller work cannot help any suffix, because future
conditions depend only on the mask. Every suffix adds nonnegative bytes/work.
Discarding labels above the largest requested budget is also safe. These
arguments prove the returned frontier is exact for the relaxation. They are
author-reviewed mathematics, not proof-assistant validation. A label/time limit
raises `Limited` and returns no bound; it cannot silently truncate the optimum.
Resource limits are per cut, not a combined elapsed-time limit for the sweep.

## Evidence and replay

From repository root, Python 3.9+:

```sh
python3 research/loss-closure-round2/verify_result.py
python3 -m unittest discover -s research/loss-closure-round2 -p 'test_*.py' -v
python3 verify_all.py
```

`results.json` includes all 60 original rows, including unchanged bounds, to
avoid selecting only positive cases. An optional OR-Tools 9.15.6755 binary
integer formulation separately computes the same relaxation; all 60 optima
match this dynamic program. The published replay needs no solver dependency.
Tests compare all Pareto labels against direct enumeration of three choices per
node on 100 seeded small DAGs at three budgets, with and without forced values
(600 comparisons). They include
nonuniform sizes/costs, non-recomputable operations and multiple sinks, plus an
explicit missing-expensive-ancestor fixture, forged claims and fail-closed limits.
Sixty more random multiple-input DAGs compare complete event bounds against the
original exact temporal optimum. A sibling author-team implementation checks
1068 cut frontiers by direct ternary enumeration and 240 further temporal optima.
Every bound stays below the existing legal witness and tiny exact optimum.
The optional `optional_cp_compare.py` compares a separate binary CP-SAT model
against every cut and original budget. Its source is retained, and its dependency
is OR-Tools9.15.6755. These are author-team controls, not independent scientific review.

The favorable initial price was the relaxed loss state itself. In particular,
missing a cheap ReLU requires regeneration of missing expensive convolution
ancestors; counting only the ReLU's own cost substantially weakens the old bound.
The first optional integer probe established useful targets before the reusable
standard-library implementation was built. No solver-speed claim is made;
other research jobs ran on the same machine.

## Scope, credit and open questions

Base `a95cc1588fc57a07cfcf5a350206825e6f5b4b52`;
seed `dafc4be0863b7654352ffb2ba4a4d2df`. This suite-wide bounds assignment comes
from the donor's explicit broad follow-up, not an undisclosed random redraw.
The start, research cutoff and experiment logs are recorded in `TASK.json`.

Credit Doug Colkitt (@Mister-Meeseeks) for the model, verifier, reconciled working
targets and original loss-knapsack bound. Dependency-aware rematerialization is
established prior art; this is a stronger necessary relaxation on the frozen
project cases, not an external state-of-the-art claim. Codex AI agents for
@0xqtpie contributed the new implementation and collaborating author review.

Open questions: independently review the trace-to-set lemmas and Pareto DP;
strengthen the relaxation with temporal allocation or repeated-replay charges;
close the remaining transformer gaps with full witnesses or temporal proofs.
Independent scientific review, proof-assistant validation, autograd fidelity,
GPU/total training memory, and training-speed gains were not checked.
