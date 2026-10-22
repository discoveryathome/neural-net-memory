# Transformer peak and work optima by checked finite closures

This package proposes a matching computational lower bound for the frozen
`transformer-b4-t128` graph at additional-forward budget 478,150,656. Its known
13-unit schedule peaks at 1,703,936 bytes and spends 421,494,784 additional work.
The unrestricted favorable-tail search excludes 12 units (1,572,864 bytes).
Since every allocation is a multiple of 131,072 bytes, exclusion establishes
the 13-unit optimum under `activation-memory/v1`, subject to proof and
implementation review. The included upper certificate is copied from the
retention-transfer / PR6 package with its original metadata intact.

The evidence is author-checked. Separate implementations, replication and
cross-agent reviews within the same AI-assisted author team are identified
explicitly; independent scientific review and maintainer acceptance remain
pending. This is an activation-model result, with no measured GPU claim.

## Minimum work at 13 and 14 allocation units

The self-contained work-optimum/ extension excludes every schedule with less than
421,494,784 extra work at 1,703,936 bytes (13 units), and less than 355,270,656
at 1,835,008 bytes (14 units). The unchanged verifier accepts matching full
witnesses. The 13-unit positive is the credited PR6 trace; it is replayed at both
its original 478,150,656 budget and its exact work price. The 14-unit positive is
copied from the same team's allocation-curve constructor, also available in PR14.
This extension needs no other PR at runtime.

These close work gaps for existing schedules; they add no new construction or
original fixed-budget peak win. The parent default replay runs both work checks
after its original 12-unit peak exclusion. The extra replay regenerates and audits
18 tables (2,042,879 transitions), enumerates all 83,007 / 585,481 necessary cut
seeds, and checks all outgoing edges of 172,238 / 1,783 closed labels with a
separately authored Python checker. Each case rejects nine semantic proof
forgeries, including a raised tight label and an omitted tight successor; matching
native controls reconstruct complete legal positive schedules.

The nested capacity bound reserves each earlier block's minimum occupancy until
its own output's final saved read. Those endpoints are nested. Therefore an
earlier prefix of minima reduces the actual local capacity available to every
later block, while forward costs remain assigned to disjoint owners. The global
claim uses this admissibility argument, the complete mandatory-cut cover, the
normalization mapping, the checked closure, and matching whole witnesses together.
Native exhaustion alone is an encoded-tail result. See work-optimum/PROOF.md for
the full proof obligations and work-optimum/VERIFY.json for limits and receipts.
All checks and reviews remain within one AI-assisted author team.

## Replay and retained evidence

From the repository root, with Python 3.10+ and a C++17 compiler on a
little-endian POSIX host (Clang/GCC builtins and `sys/resource.h` are used):

```sh
python3 -B research/native-transformer-middle-proof-round2/replay.py
python3 -B verify_all.py
```

The recorded replays used macOS 15.5 arm64 with Apple Clang. Linux and Windows
were not tested; platforms lacking the POSIX RSS probe need a port of that
boundedness check.

The donated session prefixes every execution with its network-denied,
workspace-write-only sandbox:

```sh
sandbox-exec -f "$SESSION/research.sb" /opt/homebrew/bin/python3 -B \
  research/native-transformer-middle-proof-round2/replay.py
```

Generated executables, binary tables, the 24 MB closed-label dump, logs and
temporary files belong in `generated/` (or `--out`), and are not committed.
The replay compiles the source, regenerates and independently audits every
required pattern table, reconstructs the complete critical-cut seed set,
exhausts the native queue, and checks the closed label set with a separately
authored implementation. It also checks semantic forgeries, unreduced tiny
controls, the matching upper certificate and a legal auxiliary positive trace.
`SOURCE.json`, `TASK.json` and `VERIFY.json` pin source, scope and results.
No frozen graph, verifier, baseline or accepted frontier record is edited.

The original complete native run expanded all 1,002,736 distinct labels,
generated 82,502,307 reduced edges, and finished in 20.91 seconds at about
195 MB RSS. It used 1,274,821 immutable parent records, below its ten-million
record and 120-second limits. Every layer closed and the queue was empty.
The dump-only replay reproduced those counts. Verification receipts report
the additional checker and database-audit costs separately.

## Auxiliary 12-unit construction

At an explicitly auxiliary allowance of 540,246,016, a complete schedule peaks at
1,572,864 bytes (12 units). The source trace in controls/traces/ allows
600,000,000 work and actually spends 540,246,016. The exact-budget copy in
controls/auxiliary12-exact-work-budget.json preserves every action and claim.
check_auxiliary12.py verifies both copies, checks their action identity, and
retags a negative control to the original 478,150,656 allowance, which rejects
on actual recomputation work. The default replay runs these checks.

The strongest applicable pre-round trace at at most 12 units uses 737,935,360
work; the auxiliary schedule reduces that by 26.79%. Its minimum possible work
remains open. This is an intermediate work-curve improvement; it is not a
12-unit witness at the original middle budget and is not an extra fixed-budget
benchmark win. Credit and the unchanged source trace are preserved.

## Every global 12-unit schedule has a suffix in this search

At the first `b3_gelu` allocation, every one of its 54 ancestors, including
itself, has executed. Its ancestor set is exactly the first 54 graph nodes.
Only `b3_down` and `b3_residual2` remain unseen, and their first order is forced.
Backward has not started because the loss barrier requires every first forward.

The immutable input costs one unit; `b3_up` and newly allocated `b3_gelu` cost
four each. They coexist before any subsequent input drop. At a 12-unit cap,
the remaining survivors can be at most three of the 38 one-unit ancestor
values; no other four-unit value fits. Enumerating all subsets of size zero
through three gives exactly 9,178 states. Their seen set is the 54 ancestors,
their backward-done set is empty, and their initial charged work is set to
zero. Giving away all earlier repeated work is favorable.

Consequently every globally feasible schedule has a completion in this
necessary suffix problem within the global budget. The serialization chosen
for the already seen prefix does not restrict its historical order. After
the cut, the only first forwards are the two forced terminal nodes; all
dependency-ready regenerations remain available. Both terminal allocations
and the loss barrier are retained. Omitting those allocations is a different,
weaker relaxation and does not prove this result.

## Reduced actions preserve existence

The native state is `(live, first-progress, backward-done)`, with the immutable
input counted separately. A forward allocates its absent output while all
dependencies remain resident. A repeated forward charges its full declared
cost; each remaining first forward is free additional work. Explicit saved
reads and consumer-ready backward order are preserved.

Three reductions remove redundant zero-cost choices:

1. Seal loss as soon as all first forwards and sinks are present, then execute
   every ready backward eagerly. These actions allocate nothing, spend no
   forward work, remove no tensor, and only relax later backward obligations.
   The native reverse-topological pass and the checker's ready fixed point
   compute the same closure.
2. After loss, drop values outside the ancestor closure of unfinished saved
   reads. Such values cannot help a remaining read or its regeneration.
   A completed node's descendants' backwards are complete; because saved
   reads belong to self/ancestors, its later forwards also cannot help.
3. Postpone free drops until an allocation needs space, and enumerate every
   inclusion-minimal set of nondependency residents that supplies the deficit.
   A resident superset can simulate a smaller set by delaying its drops; if
   a repeated output is already present, omit that forward and save work.
   Keeping extra values cannot obstruct an action because they may be dropped
   before its allocation. All forward dependencies stay protected. With
   one/four-unit sizes, a positive deficit is at most four; a minimal eviction
   is one four-unit tensor or exactly `deficit` one-unit tensors. Native subset
   DFS and separate checker combination enumeration implement this differently.

The unreduced control oracle permits arbitrary individual drops, arbitrary
legal backwards, and useful or useless repeat forwards. Its comparisons test
these reductions rather than mirroring their implementation.

## Pattern bounds and cost ownership

Each forward cost belongs to exactly one of four 14-node blocks. A local
projection counts the one-unit global immutable input, while its block-entry
input is always available for free. It omits cross-block delays. This is
favorable even when the actual block-entry tensor is absent.

The backward table keeps the 12-value ancestor closure of saved reads, plus
all 14 backward-done bits. Its use requires all 12 forwards already seen.
Every future local forward therefore charges its full repeated cost. The
output-demand table keeps all 14 live bits, requires all 14 seen and no local
backward complete, and requires output availability before allowing immediate
local backward. Its next-block norm1 saved read must still be pending.

Before loss, the final-block terminal-phase table keeps 13 live bits through
down, with two phases: down unseen or down seen; residual2 remains unseen.
The first down and residual2 forwards are free. The residual2 allocation must
fit before the loss/backward continuation. All first 12 values must already
be seen, and no local backward may have run. Its terminal value is the audited
backward table after the free residual2 allocation. The table covers every
owned final-block forward cost; no outside down/residual2 charge is added to
this candidate.

The current owned bound `c_i` is the maximum of applicable candidates for
block `i`: missing-seen-ancestor own work, backward-table work plus missing
own work outside its 12-value coverage, output demand, and the preloss
terminal phase. Per-block maxima are summed over disjoint cost owners.

The table generators use reverse Dijkstra. Separately authored auditors
reconstruct every legal edge, check Bellman inequalities and terminal values,
and verify tight terminal paths from every finite state. They bind local node
fields to the frozen graph; a metadata graph-hash assertion alone is
insufficient. Semantic table forgeries include rehashed wrong costs, wrong
capacity, invalid memory states and incorrect distances. All required data
comes from backward caps 9–12, terminal-phase caps 9–12, and output-demand
cap12. No nested, free-terminal, mandatory-drop or external PR data is needed.

## Region minima bind cache transfers to simultaneous capacity

Let `j` be the highest block with unfinished backward work. All later blocks
are complete. Every earlier backward is blocked until block `j`'s norm1
backward reads its input. Norm1 is an ancestor of every node in its block, so
this read is the block's final backward action. Let `T_j` be the state
immediately **before that saved read**, including all allocations up to it.
The interval must stop there, before any subsequent tensor drop.

For each earlier region `i<j`, let `r_i` be its current owned allocation units
and let `m_i` be its minimum owned units over the remaining interval through
`T_j`. Then `0 <= m_i <= r_i`. At every moment of that interval region `i`
holds at least `m_i` units, even if its cache changes identity from proj to
residual1, or to another tensor. The target block's complete remaining
execution therefore projects into capacity `12 - sum(m_i)`, still including
the immutable input. The stored cap9 table is a favorable larger-cap fallback
when that expression is below nine. Before loss the target uses its actual
terminal phase; after loss it uses its actual backward-done projection.

At a moment attaining region `i`'s minimum, all its forwards were already
seen, no local backward has run, and its output's next-norm1 saved read is
still future. Its future owned work is at least

`E(m) = min output_demand_cap12[L] over all local live sets with owned_units(L) <= m`.

`E` is computed from the audited table, excluding the standing global input
from owned units. Its first entries are
`[155123712, 111280128, 77529088, 69140480, ...]`.
All work before the minimum event may be ignored. This bound does not assume
that a particular cached tensor stays resident or is dropped immediately.
The included tiny positive falsifier shows why immediate removal of a useful
intermediate can overcharge: it may enable prefetch before being dropped.

For the actual vector of minima, each earlier region owes at least
`max(c_i, E(m_i))`, and target block `j` owes at least its pattern value at
the reduced capacity, maximized with `c_j`. Those cost owners are disjoint.
Minimizing this sum over every candidate vector cannot exceed the actual
partition's bound, and is therefore admissible. The native implementation
uses a small min-convolution over reserved units 0–11, rather than assuming a
specific minimum vector. It activates only after the required earlier/local
first forwards, with earlier backwards untouched and the target norm1 read
pending. It recurses to the next highest unfinished block as execution advances.

The generalization from binary empty/nonempty regions is essential: a region
may keep multiple units while the target executes. Current allocations bound
all enumerated minima. The proof uses a common endpoint `T_j` and requires no
unproved ordering among different regions' minimum events.

## Closed labels remove reliance on queue correctness

The emitted label set has 1,002,736 rows. Each 24-byte little-endian row is
`(LP, backward_done, spent)`, where LP packs live bits 0–55 and progress in
bits 56–63. The separate checker reconstructs all 9,178 seeds and every
reduced edge. A seed or target must have a label no greater than the offered
spent cost, or an independently computed admissible bound must exceed its
remaining budget. No labeled state may be a complete backward goal.

If a feasible reduced completion existed, induction along its actions would
give every visited state a label no greater than actual spent work. A
necessary next edge cannot be bound-pruned because its actual suffix would
contradict that bound. Closure therefore labels its complete goal, a
contradiction. This finite argument does not trust the native priority queue,
hash table, stale entries, reopen handling, or parent reconstruction.
The critical-cut, projection and normalization lemmas remain explicit
mathematical review obligations.

## Controls, limits and credit

The package includes stored tiny positives, random full arbitrary-drop oracle
comparisons, legal active-bound reconstructions, and model-verifier replay.
The generic region controls cover 240 small two/three-block graphs against an
unreduced exact oracle. Their ancillary nested-bound checks are stress tests;
the native exclusion uses the common-endpoint bound described above.
Separate actual-continuation controls checked 1,130 guarded states over four
legal traces, covering active blocks 1, 2 and 3. They measured the true minima
before each target norm1 read and checked every actual-partition owned
component against actual remaining work (4,520 per-block comparisons).

Earlier searches with weaker bounds reached explicit record/time limits;
their pinned receipts are retained. Those failures imply no impossibility.
The successful run uses unrestricted regeneration and actual remaining
terminal first forwards. No new fixed benchmark rows or frozen semantics
are introduced by the auxiliary controls.

Base commit is `a95cc1588fc57a07cfcf5a350206825e6f5b4b52`, with session seed
`dafc4be0863b7654352ffb2ba4a4d2df`. Doug Colkitt / DougColkitt /
@Mister-Meeseeks authored the original project, model, graph, verifier and
trial solver. Prior retention-transfer / PR6 supplied the known 13-unit
certificate and regional exact work informing the patterns. The earlier
high-budget native proof / PR11 supplied the pinned backward/output-demand
sources, copied here so replay has no PR dependency. Codex agents developed
the native search, region-minimum proof, pattern generators/audits, separate
closed-label checker, replication and cross-agent implementation reviews
under the human contributor's authorization. These checks remain evidence
from one author team, with scientific acceptance pending.
