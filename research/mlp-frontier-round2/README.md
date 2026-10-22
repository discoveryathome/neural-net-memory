# Exact MLP peak frontiers and complete work curves

**One strict peak improvement and exact computational closure of all eight open
MLP rows.** At the unchanged mlp-b8 budget 34,078,720, the peak decreases from
45,056 to **40,960 bytes** (9.09%). The witness spends exactly 34,078,720 units
of extra forward work. Every original MLP graph/budget row now has a matching
witness and an exhaustive exclusion search at the next smaller attainable peak.

The model is activation-memory/v1; all numbers describe its logical activation
allocations, not GPU memory or runtime. Results are **author-checked**. A second
implementation and fresh verifier replay are useful checks, not independent
scientific review or maintainer acceptance. Frozen graphs, model, core verifier,
and accepted/working records are unchanged.

Base: a95cc1588fc57a07cfcf5a350206825e6f5b4b52.
Seed: dafc4be0863b7654352ffb2ba4a4d2df.
Session began 2026-10-21 22:37:20 UTC. The assigned four-hour session stops new
research at 2026-10-22 01:37:20 UTC; this MLP task exhausted its original rows
early. TASK.json, SOURCES.json, VERIFY.json, and results.json pin the task,
source hashes, measured searches, replay commands, and limitations.

## Results

All memory sizes are multiples of 4,096 bytes. For each candidate peak P, both
solvers exhaust every feasible state at cap P−4,096 and the original budget.
Consequently no smaller attainable peak exists, provided the exactness arguments
below and their implementations are correct.

| Graph | Fixed budget | Previous peak | Exact peak | Minimum extra work at that peak |
|---|---:|---:|---:|---:|
| mlp-b4 | 0 | 151,552 | 151,552 | 0 |
| mlp-b4 | 2,129,920 | 86,016 | 86,016 | 1,146,880 |
| mlp-b4 | 4,259,840 | 53,248 | 53,248 | 3,244,032 |
| mlp-b4 | 8,519,680 | 45,056 | 45,056 | 6,422,528 |
| mlp-b4 | 17,039,360 | 40,960 | 40,960 | 8,552,448 |
| mlp-b8 | 0 | 299,008 | 299,008 | 0 |
| mlp-b8 | 4,259,840 | 135,168 | 135,168 | 3,375,104 |
| mlp-b8 | 8,519,680 | 69,632 | 69,632 | 7,569,408 |
| mlp-b8 | 17,039,360 | 53,248 | 53,248 | 15,007,744 |
| mlp-b8 | 34,078,720 | 45,056 | **40,960** | 34,078,720 |

Tied peaks are replications and exactness contributions; reduced work alone is not
counted as a primary record. The zero-budget rows were already settled. The eight
nonzero rows are proposed in proposed-frontiers.json; only the final row changes
its primary score. No authoritative record is edited.

Before constructing larger schedules, the favorable fully charged local-cap
test found that 36,864 bytes needs at least 21,299,200 extra work for mlp-b4 and
93,716,480 for mlp-b8. Both exceed their largest original budgets. These two
certificates use explicitly labeled diagnostic budgets; they are not new frozen
challenge rows or frontier proposals. Below 36,864 bytes is impossible even with
unlimited recomputation: immutable x (4,096), UP input (16,384), and GELU output
(16,384) must coexist during every UP→GELU allocation.

## Complete fixed-memory work curves

The work-curve/ extension reconstructs the minimum extra forward work at every
integer memory cap from the universal nine-unit floor to zero work: 29 caps for
mlp-b4 (9..37) and 65 for mlp-b8 (9..73), in units of 4,096 bytes. The compact
representation has 34 nondominated steps. Each of the 94 positive schedules is
checked by the unchanged verifier; all 92 positive-work caps have exhaustive
work-minus-one exclusions. Ten replays use the original benchmark budgets.
The default replay below runs this extension too, using a temporary directory.

This adds schedules between the original benchmark points, including mlp-b4
at 12 units (4,325,376 to 4,292,608 work) and mlp-b8 at 11 units
(31,981,568 to 21,364,736) and 14 units (12,877,824 to 11,829,248).
These comparisons use the strongest applicable pre-round certificates, as
recorded in work-curve/COMPARISON.json; they are auxiliary curve improvements,
not additional original fixed-budget peak wins. The parent cap-nine diagnostic
prices already existed earlier in this round and are not counted again.

The chain normalization proof below applies to all these finite caps. The
mandatory UP/GELU allocation proves the floor at every budget. With zero extra
work, every positive-cost saved value must survive its first forward evaluation
until the relevant backward; hence all values coexist at the final first forward.
The zero-work tails begin at 37 and 73 units. See work-curve/README.md for the
full scope, compact step tables, limits, evidence, and same-author-team review.

## Exactness argument

Number chain nodes 0 through n−1 and write −1 for the immutable input. Each
operation i depends only on i−1 and its backward requires exactly i−1. The
implementation rejects graphs that fail these conditions. Every node must first
execute before loss, including the sink. Forward outputs allocate before any
input drop; each transition checks the complete live mask plus output.

1. **Seen prefixes and backward suffixes are exact coordinates.** The first
   evaluation of i needs i−1, so first evaluations follow chain order. Consumer
   readiness forces backward order n−1 through 0. These are properties of this
   graph family, not extra scheduling constraints.
2. **Immediate loss is safe.** At the first execution of the terminal sink, every
   node has been evaluated and the sole sink is live. Insert loss there. Delaying
   any original pre-loss regeneration or drop until after this earlier loss
   changes no forward/drop precondition, allocation, or cost and only permits
   backwards sooner.
3. **Eager backward is safe.** A ready backward allocates no forward tensor,
   consumes no forward tensor, and has no recomputation cost. Move it before
   intervening forward/drop actions while its required parent is live. It only
   makes the next backward ready; all earlier forward actions remain legal.
4. **Useless suffixes may be dropped.** If k is the next backward, only values
   0 through k−1 can ever be required again. Any regeneration useful for them
   also uses only their ancestors. Values k and above can be dropped immediately,
   and future executions of them can be omitted. Neither transformation increases
   memory or work. After eager backward k, its just-used parent becomes part of
   that useless suffix.
5. **All remaining choices are enumerated.** From each normalized state, the
   search enumerates every individual legal drop and every absent output whose
   immediate parent is live. Repeats incur their complete declared forward cost;
   first executions cost zero extra work. Non-recomputable repeats are forbidden.
   Normalization emits actual legal loss/backward/drop actions, reconstructed
   into the certificate rather than assumed by the verifier.
6. **The remaining-work bound is admissible.** Before loss, every absent
   already-seen activation among 0 through min(m−1,n−2) is needed by a future
   backward. After loss with next backward k, the same holds among 0 through k−1.
   Every such absent value must execute at least once more. Summing their own
   costs, while ignoring the work to regenerate their dependencies, cannot
   overestimate remaining work. Pruning when spent plus this bound exceeds B
   therefore removes no feasible completion.
7. **Dijkstra and exhaustion.** States retain the live mask and exact progress.
   A lower spent-work label dominates a higher one at the same state because
   future legality and memory depend only on these coordinates. Nonnegative edge
   costs make the first removed goal a minimum-work schedule at the fixed cap.
   Exhaustion with no goal excludes every schedule at that cap and budget, by
   the normalization argument. A state/time cap raises Limited; it never
   returns an infeasibility or optimum claim.

The generic reference_fixed_cap.py keeps the full (live, seen, backward_done,
loss_sealed) state and enumerates every normative transition. It does not use
prefix/suffix compression, eager backward, immediate loss, or dead-suffix removal.
It shares the independently valid absent-required-value work bound. It exhausts
all ten exclusion cases, and confirms the improved positive witness's exact
minimum work. This reduces dependence on the chain-normalization implementation;
it is still code by the same author team.

## Replay

From the repository root, with any Python 3.9+ standard-library installation:

~~~sh
python3 -B research/mlp-frontier-round2/test_chain_exact.py
python3 -B research/mlp-frontier-round2/replay.py
python3 -B verifier.py benchmarks/graphs/mlp-b8.json research/mlp-frontier-round2/certificates/mlp-b8-b34078720-p40960.json --budget 34078720
python3 -B verify_all.py
~~~

The donor session ran every project/prototype/test invocation under its
network-denying, session-write-only sandbox-exec profile; exact commands are
recorded in VERIFY.json. replay.py checks pinned source hashes, fixed graph
identities and working targets, verifies stored witnesses with the unchanged
checker, reconstructs every stored action sequence and claim exactly, and repeats
all searches. Timing metadata is measured anew; witness actions are deterministic.
--record is the authoring mode that rewrites this package's measured outputs.

The six tests cover 800 randomized chain/cap/budget comparisons with the
unnormalized solver, ten comparisons with the original independent minimax
implementation on both fixed tiny chains, output-before-input-free accounting,
explicit resource-limit behavior, unsupported backward semantics, and six mutated
certificates rejected by the unchanged checker.

The original fixed-row search replay took about 3.2 seconds and peaked at about
91 MB process RSS on this session's host. These are local observations on a
concurrently used machine, not controlled performance claims.

## Failed attempts and limitations

The first generic small-control search at the favorable b4 cap failed to find a
schedule at its largest original budget. Unpruned specialized b4 searches then
exhausted all four improving caps. An early object-heavy b8 low-budget search hit
500,000 states: that attempt supports no infeasibility claim. Compact parent
encoding and the admissible work bound subsequently exhausted that same case in
38,015 states, and the full-state reference separately reproduced exhaustion.
The original exploratory logs are preserved under logs/. Early exploratory source
files were edited in place and not retained; their logs are historical context.
The final proof computations are rerun with the retained, hash-pinned sources.

This is a replayable finite computation with a mathematical exactness argument,
not a machine-checked proof. The generic reference's work bound still needs the
same elementary cost argument; full semantic/source review remains valuable.
No modern external solver, real training, GPU measurement, exporter audit, or
hardware memory benefit is claimed. No result applies to a graph with arbitrary
saved requirements, branching, mutation, aliasing, offload, or in-place reuse.

## Open next questions

- Review the fixed-cap exclusion proof and both implementations, especially
  the absent-required-value bound and strict specialization guards.
- Incorporate valid proposals only after independent replay and maintainer
  review; keep the original frozen records and trial unchanged.
- For a separately authorized future task, extend exact state compression to
  branching graphs or audited workload exports. The original MLP rows leave no
  unresolved peak gap under this computation.

## Credit

AI-assisted research and implementation by Codex. The analytic graphs, normative
model, original exact solver, trial mechanisms, and 17 known trial improvements
are credited to Doug Colkitt / [@Mister-Meeseeks](https://github.com/Mister-Meeseeks)
and the repository's recorded contributors. The 30-minute trial is a mandatory
starting target, not a new result here.

The fixed-cap formulation and initial positive controls build on the
regional_exact.py code from the prior
[PR 6 retention-transfer package](https://github.com/discoveryathome/neural-net-memory/pull/6).
Its source hash and package metadata are pinned in SOURCES.json. The chain
compression and generic reference added here use the established finite pebbling
state-search model; no new optimization paradigm is claimed. Cross-agent review
is author-team implementation review, not independent scientific acceptance.
