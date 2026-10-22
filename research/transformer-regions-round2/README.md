# Better transformer memory and recomputation schedules

Two new schedules strictly improve the frozen `transformer-b2-t64` working rows.
All allocations, immutable inputs, first forwards, loss and backward dependencies
are checked by the unchanged standalone verifier. These are author-checked model
results, with independent review and maintainer acceptance pending.

| Additional-forward budget | Working peak | New peak | Reduction | New additional work |
|---:|---:|---:|---:|---:|
| 27705344 |1310720 |1245184 |5.00% |26869760 |
| 110821376 |720896 |655360 |9.09% |106725376 |

At the already minimal 294,912-byte one-block peak, an additional exact search
reduces work from the strongest prior 24,854,528 certificate to **23,281,664
(6.33% less)**, within original budget 26,615,808. It also fits the highest
budget; that reuse is not counted as another new frontier point. The certificate
at budget 53,231,616 previously used more work, so comparison uses the stronger
lower-budget predecessor. Every prior matching-graph certificate in the pinned
base was replayed before selecting this comparison.
The one-block Dijkstra includes all legal first-forward, drop and backward orders.
It reconstructs the positive and exhausts the entire fixed-cap domain one work
unit below 23,281,664. This is a global minimum-work proposal at that fixed peak;
independent scientific review remains pending.
The new order avoids one repeated K projection and one norm, while repeating
the cheaper attention scores and probabilities once more. The net saving is
1,572,864 work units at the same peak.

The low-budget witness keeps `b0_q`, `b0_k`, `b0_residual1` and `b0_up` during
the second block. Its last block uses 720896 local bytes and 17629184 extra work;
the earlier block's cached backward region uses 9240576 work. The global verifier
charges every retained tensor outside each region. The other witness retains the
block-entry checkpoint, uses a 589824-byte last-block region, then a 655360-byte
backward region; their extra work is 51003392 and 55721984 respectively.

The constructor extends the prior PR6 one-block composition to all three pinned
transformer graphs and explicit earlier-block retention sets. Regional optima are
for their stated start conditions. Multiple-block composition has no global optimum claim. The one-block search covers the complete graph.
Backward-only regions begin after all forwards have happened: every replay costs
work. Their deliberately large validation prefix is removed when constructing the
real full-graph schedule; final full-graph memory is never excluded.

## Replay

From the repository root, Python 3.9 or later, standard library only:

```sh
python3 research/transformer-regions-round2/verify_result.py --reconstruct
python3 -m unittest discover -s research/transformer-regions-round2 -p 'test_*.py' -v
python3 verify_all.py
```

The first command verifies pinned repository sources, checks all three complete
certificates, reconstructs their exact action lists, reruns the small fixed-cap
searches and rebuilds the structural cut. It imports no optional solver. The
certificates also pass directly to `verifier.py` with their original budgets from
the table. Accepted and working records are untouched.

Programmatic construction:

```python
from compose_schedule import compose
# Use the frozen b2 graph. The retained names are local to its first block.
actions, stats = compose(graph, 1245184, 27705344,
    retained=[['b0_q', 'b0_k', 'b0_residual1', 'b0_up']])
```

## Exact one-block and structural results

The complete one-block frozen graph admits exact minimum-work search. At cap
360448 it needs 7725056 additional work, exceeding budget 6653952. At cap 327680
it needs 15851520, exceeding budget 13307904. Since every allocation is a multiple
of 32768, these searches establish the existing peaks 393216 and 360448 at those
budgets. The checked fixed-cap certificates use a larger auxiliary budget; they
are not smaller-peak witnesses at the original challenges.

The inherited last-barrier classifier also transfers to b2. Its two barriers are
`b0_gelu` and `b1_gelu`, each filling 589824 bytes with the immutable input and
UP/GELU tensors. Before the first `b1_residual2`, take the last of these events.
No other activation survives it; even with free unlimited-memory execution of
all other operations, neither forced state reaches the sink without another
barrier. Thus 589824 is impossible and the whole-allocation floor is 655360 at
every budget. Our 110821376-budget witness and the predecessor's 221642752-budget
witness meet it. This is a mathematical cut with an executable finite closure
check, not a proof-assistant artifact or independent review.

The separate [event-cut bound proposal](https://github.com/discoveryathome/neural-net-memory/pull/9)
provides a matching 1245184 lower bound for the new low-budget witness and matches
the unchanged 851968-byte row at budget 55410688. This package does not import that
proposal or rely on it for schedule legality.

## Bounded unsuccessful work and open questions

Thirty b2 retention subsets at the tighter 55410688 budget gave no 786432-byte
construction in that domain; the 512-subset low-budget domain produced the new
witness. Higher-cap regional probes and finite optional-slot attempts hit declared
limits or failed within their supplied trace domains. These outcomes are not
proofs of global impossibility.

The inherited b4 result at budget 478150656 already uses 1703936 bytes and
421494784 extra work. It is a positive control, not a new result here. Can a legal
1572864-byte schedule fit the same budget, or can a stronger bound exclude it?
The later PR13 necessary-tail exclusion now proposes the matching 13-unit optimum. Earlier limited scratch searches and larger-budget auxiliary witnesses remain non-wins.

Global b4 minimum work, independent review, native Checkmate/DTR/Moccasin
comparisons, exporter/autograd fidelity and actual GPU memory or speed are not
checked. No accepted frontier, graph, model or core verifier is changed, and no
GPU or external SOTA claim is made.

## Provenance

Base `a95cc1588fc57a07cfcf5a350206825e6f5b4b52`; seed
`dafc4be0863b7654352ffb2ba4a4d2df`; explicit user-assigned transformer-family scope.
`TASK.json`, `SOURCES.json`, `VERIFY.json` and `experiments.jsonl` pin parameters,
inputs, source hashes, limits, successes, failures and review status. Experiment
source snapshots are retained in the session handoff; exact winning action replay
is the public reproducibility contract.

Codex AI agent for @0xqtpie authored this follow-up. Credit Doug Colkitt
(@Mister-Meeseeks) for the model, frozen verifier, predecessor schedules and trial
research; prior PR6 for the regional solver and composition; and the prior
barrier-cut package for the last-barrier classifier. All new results remain
author-checked. Code and project text retain the repository's MIT license.

The [complete one-block memory/work curve](work-curve/README.md) extends the exact result to every integral cap from9 through19 allocation units. All eleven nondominated points reconstruct full schedules; ten nonzero points exhaust one less work unit. These intermediate Pareto points expand coverage rather than adding fixed-benchmark wins.
