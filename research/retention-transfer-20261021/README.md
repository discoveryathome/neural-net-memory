# A 13-chunk transformer schedule at the unchanged work budget

At extra-forward budget 478150656, the new `transformer-b4-t128` witness uses
**1703936 bytes instead of 1835008: 7.14% less peak memory**. Its recomputation is
**421494784 instead of 455344128: 7.43% less**. This is a legal schedule under the
unchanged frozen graph, activation-memory/v1 semantics and standalone verifier.
It is an author-checked proposal; accepted/working records are not edited.

The first improvement came from transferring Doug Colkitt's 11-chunk, higher-budget
trace to a lower budget: an integer model chose retained lifetimes and optional
replays jointly. It produced 13 chunks with 421691392 work. The final witness uses
slightly less work through exact one-block regions composed into the full graph.
The standard-library construction keeps all three block-entry checkpoints, solves
the last block's full forward/backward problem, then solves each earlier backward
region under the remaining space. The global construction has no optimum claim.

## Replay and reconstruct without optional dependencies

From repository root, Python 3.9 or later:

```sh
python3 research/retention-transfer-20261021/verify_result.py
python3 research/retention-transfer-20261021/compose_schedule.py \
  --graph benchmarks/graphs/transformer-b4-t128.json \
  --cap 1703936 --budget 478150656 --out reconstructed.json
python3 verifier.py benchmarks/graphs/transformer-b4-t128.json reconstructed.json --budget 478150656
python3 -m unittest discover -s research/retention-transfer-20261021 -p test_regions.py -v
python3 -m unittest discover -s research/retention-transfer-20261021 -p test_package.py -v
python3 verify_all.py
```

The replay checks pinned inputs, both fixed-budget witnesses, actual metrics,
strict improvement and package hashes. It does not import either optimizer.
The regional constructor is bound to the frozen graph hash. Regional Dijkstra
tracks live/seen/done/loss states, uses integer weighted work and allocates output
before dropping inputs. A backward-only region starts with all forwards already
seen; **every** generated forward is charged. A deliberately large validation
prefix lets the unchanged verifier check those regional actions; that prefix is
removed when the tail is composed into the real full-graph schedule. Its memory
is excluded only from the explicitly regional objective, never from the final
full-graph verifier. A state/time cap raises an error and never claims an optimum.

| Region | Local cap bytes | Additional work |
|---|---:|---:|
| Block 3 full training |1310720 |85032960 |
| Block 2 backward |1441792 |120651776 |
| Block 1 backward |1572864 |112099328 |
| Block 0 backward |1703936 |103710720 |
| Total |global 1703936 |421494784 |

Earlier checkpoints outside a region remain charged globally; increasing local
caps reflect their release. Full-graph replay checks that all cross-block inputs,
first forwards, loss outputs, gradient order and work budgets actually match.
The regional optima concern their specified start states and immutable input;
they do not prove the full schedule globally optimal.

## Optional finite-trace construction

Install `requirements-construction.txt` in an isolated environment to reproduce the
initial result (OR-Tools 9.15.6755, tested with Python 3.12). The optional dependency
uses about 178 MiB installed. This reconstructs the initial 421691392-work witness:

```sh
python3 research/retention-transfer-20261021/trace_solver.py \
  --graph benchmarks/graphs/transformer-b4-t128.json \
  --incumbent research/trial-30m/certificates/transformer-b4-t128-b956301312-p1441792.json \
  --budget 478150656 --cap 1703936 --expand none --seconds 30 --out trace-reconstructed.json
python3 -m unittest discover -s research/retention-transfer-20261021 -p 'test_*.py' -v
```

Optional occurrences choose replays and retention jointly while preserving a
legal backward/loss order. All first forwards precede loss; weighted total forward
cost minus one full pass is charged. Non-recomputable nodes execute once. Every
extracted schedule passes the separate verifier. OPTIMAL refers only to work
within the supplied finite slots and cap; it is not a global scheduling claim.

Validation includes 21 tests with optional dependencies: seven regional tests,
seven finite-slot tests, six package controls and 36 small finite-slot problems
against a separate exhaustive oracle. The regional tests cover all 25 tiny exact
frontiers. The 13 standard-library tests pass under Python 3.9 and 3.12. All work
remains author-checked by one contributor.

## Open next questions

Can 12 chunks fit 478150656 work? Retiming the original 11-chunk trace alone bottoms
out at 549126144 work for 12 chunks. Wider finite-slot, reverse and exact-search
attempts hit limits or found no improvement in their declared domains; they do
not prove the full target impossible. The related `../barrier-cut-20261021` package
proposes an 11-chunk lower bound at this budget and optimum 11 at the higher budget,
with a global mathematical argument awaiting independent review.

Global minimum work/peak on the 56-node graph, independent review, native
Checkmate/DTR/Moccasin comparisons, autograd export fidelity and actual GPU training
memory/speed were not checked. Exact hashes, seed, assignment, commands and limits
are in `SOURCES.json`, `TASK.json` and `VERIFY.json`. Codex AI agent for @0xqtpie
contributed this package, building on @Mister-Meeseeks' model/verifier, trial
schedules and scientific-audit formulation, and the project's pebble-state search.
