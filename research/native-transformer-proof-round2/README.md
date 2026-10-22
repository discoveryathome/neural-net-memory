# A checked finite exclusion for the high-budget transformer row

For the frozen `transformer-b4-t128` graph at additional-forward budget
956,301,312, this package excludes a peak of 1,310,720 bytes (10 allocation
units). The existing verified 1,441,792-byte (11-unit) schedule uses 737,935,360
additional work. Every allocation is a multiple of 131,072 bytes, so these two
facts establish the 11-unit optimum under `activation-memory/v1`, subject to
review of the proof and implementation below. The graph hash is
`7d60aaf32c25d4d000872f9d317cdb0cbc71c929307eb69faf7e974c795d5854`.

The evidence is author-checked, with separately authored implementation checks
within the same AI-assisted author team. Independent scientific review and
maintainer acceptance remain pending. This is a computational bound in the
declared activation model; it makes no measured GPU claim.

## Replay

From the repository root, use Python 3.10+ and a C++17 compiler:

```sh
python3 -B research/native-transformer-proof-round2/replay.py
python3 -B verify_all.py
```

The donated session used its network-denied, workspace-write-only profile:

```sh
sandbox-exec -f "$SESSION/research.sb" /opt/homebrew/bin/python3 -B \
  research/native-transformer-proof-round2/replay.py
```

The script compiles the source, generates both pattern databases, audits their
complete Bellman graphs, rejects forged tables, generates the critical-cut
search input, exhausts the native queue, and independently checks every edge of
the resulting closed label set. It then rejects forged proof inputs, verifies
the existing matching upper schedule, compares against an unreduced oracle on
720 random cases, checks all 25 stored tiny controls, and reproduces a known
13-unit schedule through the unchanged verifier. The 13-unit control is
constructive and may restrict regeneration; the exclusion uses unrestricted
regeneration (`demand_mode=0`). `--skip-controls` omits only the additional
random/tiny/13-unit controls, never the complete proof or database audits.

Generated executables, tables, 10 MB label dumps, temporary files, and replay
logs stay in `generated/` by default. They are deliberately not committed.
`--out` chooses another writable scratch directory. No downloaded dependencies
are needed. The original run took about 1.1 seconds for native exhaustion and
24 seconds for the separate Python edge check; full integrated replay timings
are in `VERIFY.json`. A compiler or resource failure is a failed replay, never
an exclusion result.

## Why this cut covers every feasible global schedule

Let one unit be 131,072 bytes. Consider the instant immediately after the first
`b3_gelu` forward allocation, before any subsequent drop. Its internal ancestor
set, including itself, is exactly the first 54 graph nodes. Every one has
already executed. Neither `b3_down` nor `b3_residual2` can have executed because
both depend transitively on this first GELU. They are the only two remaining
nodes, and their first execution order is forced: down, then residual2.
Backward cannot have started because the loss barrier requires every first
forward.

At this instant the immutable input `x` costs one unit, `b3_up` costs four, and
the newly allocated `b3_gelu` costs four. All three coexist by the normative
output-before-input-drop rule. At a 10-unit peak, at most one additional
one-unit tensor can be resident; no other four-unit tensor fits. There are 38
eligible one-unit nodes among the 54 ancestors, giving exactly 39 survivor sets
(empty or one survivor). The input exporter and separate checker reconstruct
this complete set directly from the pinned graph.

The search starts each such state with zero charged work, retaining the actual
seen set and no backward-done bits. This gives away all repeated work before
the cut. Every feasible global schedule therefore has a suffix in this
favorable problem whose cost is no greater than the global budget. The first
forward order of the preceding 54 nodes is immaterial: after the cut, only the
two forced first executions remain. No restriction on legal regeneration
order is imposed in the exclusion. Both remaining first forwards, their
output allocations, and the loss barrier are present. Omitting them is a
different, weaker relaxation which has feasible low-cost tails and cannot
justify this result.

## Complete reduced transition system

A state consists of the live internal mask, first-forward progress, and
backward-done mask. The immutable input allocation is counted separately.
Progress is 54 or 55 before loss and 57 after sealing it. Each legal next
forward may execute when its output is absent and every dependency is live.
An already seen forward costs its declared work; a first execution costs zero
additional work. Every dependency remains live while the output is allocated.
All repeated forwards permitted by the frozen graph are considered.

The following reductions preserve existence of a schedule within the cap and
budget:

1. **Eager loss and backward.** Once all first forwards and sinks are present,
   sealing loss consumes no activation or work. A ready backward also consumes
   neither, does not remove a saved value, and only enables other backwards.
   Moving these actions earlier cannot prevent a later action. The C++ code
   takes a reverse-topological pass; the checker independently takes a ready
   fixed point. These compute the same closure.
2. **Remove dead tensors after loss.** Form the ancestor closure of every
   saved value required by an unfinished backward. A tensor outside it cannot
   help any remaining saved read or its regeneration. It may be dropped and
   need never be forwarded again. A completed node's descendants' backwards
   have also completed; because saved reads are restricted to self/ancestors,
   that node cannot help an unfinished read. Skipping its later forwards is
   therefore safe. This argument depends on the validated model's ancestor
   condition and consumer-ready backward order.
3. **Delay free drops until an allocation needs space.** A resident superset
   can simulate a smaller live set by postponing its free drops. If a scheduled
   repeat forward's output is already resident, that forward can be skipped,
   saving work. Otherwise, before its allocation, choose an inclusion-minimal
   subset of the postponed drops that supplies the required space. Keep the
   dependencies protected. The resulting state retains a superset of the
   original useful residents and spends no more work. Earlier eager backward
   actions only relax the remaining obligations. Thus enumerating every
   inclusion-minimal eviction set suffices. For this graph, output sizes are
   one or four units, so a positive deficit is at most four; an inclusion-minimal
   set is one four-unit value or exactly `deficit` one-unit values. The native
   search uses a generic subset DFS, while the checker uses this distinct
   combination enumeration.

For each reduced key, the native A* retains its smallest discovered spent
cost and reopens on improvement. Immutable parent records avoid reconstructing
a path through a later modified label. Queue, time, record and RSS limits
produce explicit limit statuses and cannot emit an exhausted certificate.
The proof does not need to trust queue termination: the separate checker
verifies the closed labels themselves.

## Admissible work bounds

The basic bound starts with every unfinished saved read (and before loss,
every unseen first forward and sink), follows dependencies through absent
values, and stops at resident values. Every absent already-seen value in this
closure must execute at least once in any completion. Charge each such value's
own forward cost once. A missing non-recomputable value makes completion
impossible.

The two pattern databases provide stronger lower bounds on each block's
future owned forward costs. Block forward cost sets are disjoint.

* The backward pattern keeps the 12-value ancestor closure of local saved
  reads and all 14 local backward-done bits. The block entry is always
  available free; a standing one-unit allocation accounts for the global
  immutable input. Loss and cross-block delays are omitted. Its guard requires
  that all 12 pattern forwards were already seen, so charging each future
  local forward its full cost is valid. Add the basic bound's own costs for
  down/residual2, outside this pattern.
* The output-demand pattern keeps all 14 live values. Its guard requires all
  14 forwards seen, no local backward complete, and the next block's norm1
  backward still pending. That consumer must read the local residual2 output
  before local residual2 backward, and every other local backward is blocked
  behind it. Requiring output availability before permitting immediate local
  backward is a favorable projection. This table covers all 14 local costs,
  so no outside own-cost charge is added to this candidate.

For each block, take the maximum of its applicable basic, backward-plus-outside,
and output-demand candidates. Sum these maxima between blocks. Every candidate
lower-bounds the same block's actual future work, and the four owned cost sets
are disjoint; this combination is admissible. Guards use the actual seen/done
bits, including the two unseen terminal nodes before loss.

`pdb/replay_pdb.py` generates the tables and separately checks every legal
forward/drop/backward edge against Bellman inequalities, zero or exact terminal
costs, and a tight-edge path from every finite state to a terminal. It also
binds all local node fields to the frozen graph. Thus the audits do not trust
the reverse-Dijkstra generator or a metadata assertion of graph identity alone.
Rehashed semantic table forgeries are rejected. For cap10 the audits cover
168,468 backward-table edges and 24,366 demand-table edges.

## Why the closed labels establish exclusion

The native run emits 419,463 labels, each `(live, progress, done, spent)`. The
separate Python implementation checks every seed, state invariant and reduced
outgoing edge: a target either has a label no greater than source cost plus
edge cost, or its admissible work bound exceeds the remaining budget. It also
checks that no labeled state is a complete backward goal. All 39 seeds are
labeled with cost zero. Its full run checks 10,474,740 edges; 461,695 targets
absent from the labels are justified by the bound.

If a feasible reduced completion existed, induct along its actions: its current
state would have a label no greater than its actual spent work. A necessary
next transition cannot be bound-pruned, since an actual remaining completion
would contradict that bound. Closure therefore supplies the next label at no
greater spent cost. The complete goal would have to be labeled, a contradiction.
This finite closure argument removes reliance on the native hash table,
priority queue, stale-entry handling, or parent reconstruction for exclusion.
The mathematical cut/projection/reduction lemmas remain explicit review items.

## Search limits and unresolved row

The original-budget 12-unit case at budget 478,150,656 remains unresolved.
The unrestricted critical-cut run reached its 10-million-parent-record cap
after 68 seconds, with 7,199,339 distinct labels and minimum remaining queue
priority (`spent + lower_bound`) 457,211,904, below budget. This priority is a
diagnostic only: the popped state may be incompletely expanded on a record
limit, so it is not a certified bound on all unresolved work. Its initial favorable bounds
range from 385,187,840 to 516,718,592; a minimum seed retains b0/b1/b2 residual1
alongside the forced up/GELU. This is a limited search, with no exclusion or
optimality conclusion. `evidence/cap12-limited.jsonl` retains exact parameters,
hashes, memory and layer counts. Earlier finite-order or finite-slot failures
also do not exclude general schedules.

## Credit and provenance

Base commit: `a95cc1588fc57a07cfcf5a350206825e6f5b4b52`. Session seed:
`dafc4be0863b7654352ffb2ba4a4d2df`. The original model, graph, verifier,
trial schedules and project are by DougColkitt / @Mister-Meeseeks. The retained
13-unit control comes from the prior retention-transfer/PR6 package, with its
original metadata intact. Its regional exact solver informed the local
pattern construction and controls. This package's native state search and
cut proof, separately authored Python closure checker, and pattern database
generator/audits were produced collaboratively by Codex agents under the human
contributor's authorization. These are implementation cross-checks within one
author team, not independent scientific acceptance. `SOURCE.json`, `TASK.json`
and `VERIFY.json` pin source, task and replay evidence. No frozen graph, core
verifier, baseline or accepted record is modified.
