# Exact ResNet activation-memory staircase

The three open `resnet-b4-c32` rows are computationally settled at their unchanged
working peaks. This package supplies a complete minimum-recomputation staircase for
that fixed graph in `activation-memory/v1`. It finds **no strict peak improvement**
at an original fixed budget. Every claim is **author-checked**; independent code and
proof review, and maintainer acceptance, remain open.

Two schedules also reduce work at unchanged original peaks:

| Original budget | Peak bytes | Strongest previous work | New exact work | Reduction |
|---:|---:|---:|---:|---:|
|605,552,640|1,048,576|605,421,568|378,339,328|37.51%|
|302,776,320|1,310,720|302,645,248|189,136,896|37.51%|

The full cap4/cap5 traces are explicitly retagged to these original budgets
and replayed. An audit of every matching certificate in the pinned base and
prior PR6 trees found no cheaper predecessor at either peak. The exact
staircase supplies matching minimum-work bounds. These are secondary gains;
the peak remains unchanged. See `SECONDARY-WORK.json` and the scoped baseline
audit for exact sources and hashes.

Base: `a95cc1588fc57a07cfcf5a350206825e6f5b4b52`. Graph hash:
`fe120b9dbba356bf53b6042ad7174fd2506df22906c017502008405f9c0f354f`.
All tensor allocations, including immutable `x`, are 262,144 bytes. Costs below are
additional abstract forward work, never measured latency or GPU memory.

| Peak bytes | Total allocations including x | Exact minimum recomputation |
|---:|---:|---:|
| 1,048,576 | 4 | 378,339,328 |
| 1,310,720 | 5 | 189,136,896 |
| 1,572,864 | 6 | 151,257,088 |
| 1,835,008 | 7 | 113,442,816 |
| 2,097,152 | 8 | 75,628,544 |
| 2,359,296 | 9 | 37,814,272 |
| 2,621,440 | 10 | 0 |

Each point has a complete witness and a replayable exact search. For every nonzero
threshold, replay also exhausts the domain at one cost unit below it. A cap below
four allocations is impossible: `b1_add` must allocate its output alongside
`b0_relu2`, `b1_conv2`, and immutable `x`. Larger caps cannot improve on zero work.
Since every live allocation is an integer multiple of 262,144 bytes, these points
exhaust the graph's memory/work Pareto frontier, including budgets between the
original five challenges.

At original budgets 75,694,080; 151,388,160; and 302,776,320, the optimum peaks are
respectively 2,097,152; 1,572,864; and 1,310,720 bytes. These equal the working
witnesses. The old lower bound of 1,048,576 bytes is therefore strengthened to each
witness for all three previously open cells. No accepted or working record is edited.
The four- and five-allocation points reduce work against the strongest known
pre-round certificates at those unchanged peaks; the two secondary gains above
are not fixed-budget primary wins.

## Why this finite search is exact

Every node after the first directly depends on its immediate predecessor. Therefore
all first forwards must follow the serialized node order, and all backwards must
follow its reverse. Forward regeneration may still use any dependency-ready earlier
node, including nodes whose backwards already completed. The solver validates the
chain condition and rejects graphs outside that domain.

The logical state is `(live, seen, b)`: an internal live-tensor bit mask, the length
of the prefix that has executed at least once, and either `b=-1` before loss or the
length of the prefix whose backwards remain. Immutable inputs are implicitly live.
There is one minimum additional-work label per state. A higher-cost path to the
same state is dominated because future legality depends only on that state and the
remaining budget. Immutable parent records keep every reconstructed action path
valid when labels improve.

Three reductions preserve an optimal path:

1. Once all first forwards have run and the sink is live, move loss immediately
   before any later action. Loss changes no activation and only enables backwards;
   it removes no legal forward or drop action.
2. After loss, execute the next backward immediately whenever its saved values are
   live, repeating while possible. Backward allocates, drops, and regenerates no
   activation in this model. Moving it earlier cannot invalidate a future action:
   consumers are already complete, its requirements are satisfied now, and done
   status only enables more backwards. This depends on the declared model excluding
   gradient memory and parameter mutation.
3. Drop any tensor outside the ancestor closure of every remaining saved-value
   demand after loss. Such a value can neither satisfy a remaining backward nor
   help regenerate one of its required values. Removing it cannot increase work or
   peak. Before loss, arbitrary drops remain explicit choices.

For each normalized state, the transitions enumerate every live tensor's drop and
every absent dependency-ready forward among the seen prefix and the next unseen
node. First executions cost zero additional work; every repeated forward charges
its full positive declared cost. All input/output coexistence is checked **before**
normalization or a later drop. The loss barrier requires all first forwards and all
sinks; every backward must finish. No value is regenerated by a backward.

The admissible lower bound starts with all outstanding saved-value demands; before
loss it also includes dependencies of future first forwards and the sinks. Recursively
follow every absent demand through absent dependencies, stopping at currently live
values and immutable inputs. Each absent value in that closure that was already
seen must execute at least once in any completion. Sum its forward cost once;
unseen first executions cost zero. A required absent non-recomputable value makes
that state infeasible. This relaxation ignores repeated regeneration and memory,
so it can only underestimate remaining work. The bound is used both for budget
pruning and as the A* priority. Reopening lower-cost states is supported.

Every transition has nonnegative additional cost, and the lower bound is admissible.
Thus the first removed goal has minimum work under the fixed cap. Exhausting the
queue establishes no legal schedule in that cap/budget domain. A state or time cap
raises `Limited`; it never produces infeasibility or optimality evidence. Finding a
goal below the search's finite upper budget also proves the global minimum at that
cap: every cheaper path would itself fall inside the searched budget.

## Reproduction

Standard library only, Python 3.10 or newer. From the repository root:

```sh
python3 -B research/resnet-frontier-round2/verify_result.py
python3 -B -m unittest discover -s research/resnet-frontier-round2 -p 'test_*.py' -v
python3 -B verify_all.py
```

The donated session executed these through `sandbox-exec` with network denied and
writes confined to its session directory. Exact commands and evidence are pinned in
`VERIFY.json`; the parent baseline run already passed before research. To reproduce
one obstruction directly:

```sh
python3 -B research/resnet-frontier-round2/chain_exact.py \
  --graph benchmarks/graphs/resnet-b4-c32.json --cap 1835008 --budget 75694080 \
  --states 250000 --seconds 30 --out /your/scratch/low-budget.json
```

`RESULTS.json` pins seven witness hashes, exact thresholds, threshold-minus-one
exhaustions, all five fixed-budget consequences, and smaller ResNet controls.
`verify_result.py` checks the immutable suite graph, redoes every search, verifies
all stored certificates with the unchanged checker, and compares action sequences.
It does not trust a candidate-supplied graph or a substituted budget. The replay's
largest positive search creates 60,677 immutable records. Limits are 250,000 records
and 30 seconds per call. Local timings are uncontrolled, with sibling research jobs
running; they are not performance benchmarks.

Tests compare both feasible and immediately smaller infeasible caps against the
original unreduced minimax solver on 120 seeded nonuniform random chain/budget
pairs and all eligible tiny fixed-chain rows. They include skip dependencies,
non-recomputable nodes, self/ancestor/empty saved-value lists, and nonuniform tensor
sizes and costs. Additional controls reproduce the smaller ResNet's settled row,
require output allocation before input drops, reject non-chain inputs and malformed
limits, and fail closed on state/time exhaustion. The full core suite also
covers the repository's 25 tiny optima and negative certificates.

The ancestor bound is not necessary for correctness but materially improves search.
A separately authored generic explicit-state Dijkstra from the parallel MLP worker
uses no chain normalization. It confirms the four-allocation threshold at 11,364
states, and the four- and five-allocation original-budget exclusions at 8,019 and
44,846 states. Its low-budget seven-allocation run stops at 200,000 states without
a conclusion. This is author-team cross-checking, not independent scientific review.

An unpruned Dijkstra control confirms the 4- and 5-allocation thresholds at respectively
4,625 and 21,163 records. The same control at eight allocations stops at 250,000
records without a result; it supplies no bound. The generic trial search previously
hit 500,000 labels on the low nonzero budget. An initial test-selection attempt also
included workload rows in the original generic solver; it was interrupted and the
control set was narrowed to the declared tiny cases. These failures do not alter
the replayed exact conclusions.

## Scope, credit, and open next questions

This solves a fixed analytic macro-op graph under the existing model. It does not
validate an exporter, operator saved-tensor assumptions, gradient allocations,
convolution workspaces, hardware memory, or wall-clock speed. The implementation's
mathematical reduction and proof have not received independent review. Finite
computations are not machine-checked proof artifacts.

Credit Doug Colkitt and **@Mister-Meeseeks** for the project and task context; the
project's `search.py`, `verifier.py`, trial-30m dominance search and report for the
normative model, witness utilities, controls and prior obstruction; and the prior
retention-transfer PR6's fixed-cap regional formulation for methodological context.
No PR6 source is vendored here. The generic `reference_fixed_cap.py` control is
copied unchanged from the parallel MLP worker and credited as separately authored
within this same Codex author team. Codex AI authored this package during an explicitly
authorized research session; all evidence remains author-checked. Source hashes,
seed and exact base are in `SOURCES.json` and `TASK.json`.

Next, independently review the chain normalization proof and implementation, replay
all seven thresholds, and decide whether to reconcile the three closed working
rows. Further schedule searches on these original ResNet cases cannot improve the
proved peaks. Useful new work needs a different versioned graph/model, exporter
fidelity evidence, or a solver generalization to DAGs without forced orders.
