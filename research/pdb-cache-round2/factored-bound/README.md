# Two exact work bounds from a factored mandatory cut

For the frozen `transformer-b4-t128` graph, the minimum additional forward work
among all legal schedules with at most the stated peak is:

| Peak bytes | Allocation units | Minimum additional work |
|---:|---:|---:|
| 2,883,584 | 22 | **234,618,880** |
| 4,718,592 | 36 | **117,178,368** |

The complete saved witnesses attain these values. The necessary bound below
matches them, covering arbitrary legal first-forward, recomputation and backward
orders. This is a secondary-work result at two existing peak points. Other
peaks are diagnostics, not additional work-optimality claims.

From the repository root, standard-library Python:

```sh
python3 research/pdb-cache-round2/factored-bound/replay.py --out /path/to/scratch
```

The replay uses the parent package's `pattern_db.py` and `output_demand_db.py`,
plus the credited terminal-phase generator copied here. It regenerates every
table used, independently audits all forward edges and tight paths, checks
factoring against a separately authored direct six-coordinate enumeration,
and verifies complete witnesses and their actual per-block future work.
Generated tables and results stay under `--out`; no native binary, optional
solver, large root enumeration or precomputed binary artifact is needed.

## Mandatory cut and region minima

One unit is 131,072 bytes. At the allocation of the **first** `b3_gelu`, exactly
the first 54 graph nodes have been seen: the three earlier blocks' fourteen
nodes each and the final block's first twelve nodes. This is the exact ancestor
closure of that GELU. Its DOWN and RESIDUAL2 descendants have not had their first
forwards. No backward has run, since all first forwards must precede loss.
UP and GELU coexist at four units each, and the immutable input occupies one.

Let `C` be the global cap in units. For each earlier block `i`, let `r_i` be its
current owned allocation units. Owned allocations include all fourteen local
nodes, including DOWN and RESIDUAL2, and exclude the immutable input. If
`R=sum r_i`, the final block currently owns at most `C-1-R` units and at least
the eight forced UP/GELU units. Thus `R<=C-9`.

Let `T` be the final block's `norm1` backward saved-input read. For each earlier
block, let `m_i` be its minimum owned units from the cut through the instant
strictly before `T`. Then `0<=m_i<=r_i`. At every instant of this interval all
three earlier regions own at least their respective minima, even if they
exchange cached value identities or reach their minima at different times.
Writing `M=sum m_i`, the final block's entire remaining local computation fits
the favorable cap `C-M`, with the one global immutable-input unit still charged.
The final block completes at `T`, so no later active-block allocation lies
outside that interval.

Every earlier block's external output read is still pending until `T`: its
RESIDUAL2 backward waits for the next block's `norm1` backward, and this
dependency chain goes through the final block. Every local node has a path to
its RESIDUAL2. Therefore no earlier local backward can precede that output
read. This establishes both local output-demand bounds below.

## Local bounds and exact size summaries

Each local problem makes its block entry permanently available without
allocating it; its fixed one-unit input stands for the global immutable input.
All internal allocations, saved reads and charged old forwards remain exact.
Other regions are omitted. These choices make every local problem favorable.

For a fourteen-bit live mask `L`, let `D_C[L]` be the local output-demand table:
it requires a local output availability/read before local backwards. The read
may happen immediately when the output is live, relaxing the actual delay.
Define

```
A[r] = min D_C[L] over masks with exactly r owned units
E[m] = min A[r] for r <= m
```

At the original cut, `D_C[L_i] >= A[r_i]` lower-bounds that block's future owned
work. At the instant it reaches its actual minimum, its output read and local
backwards are still pending. Its later owned work is at least `E[m_i]`.
All work between the cut and that minimum is nonnegative. Consequently its
entire future owned work is at least `max(A[r_i], E[m_i])`.

The masks minimizing `A` and `E` need not be the same, nor jointly realizable.
Choosing them independently only weakens the lower bound. `A` is an exact-size
minimum and need not be monotone; only `E` is a prefix minimum.

For the final block, let `Z_c[s]` be the minimum phase-zero terminal-table value
over live masks with at most `s` owned units, UP and GELU present, and DOWN
absent. Its first twelve values have been seen. The first DOWN and RESIDUAL2
remain free, all old forwards are charged, and no backward precedes loss.
First sink allocation is checked before dropping inputs. At the cut, its
future owned work is therefore at least `Z_(C-M)[C-1-R]`.

The four bounds charge disjoint node-forward owners. Their sum is a lower bound
on global additional forward work. The local memory allowances are not summed.
All work before the mandatory cut is discarded, so earlier recomputation and
arbitrary first-forward orders are also covered.

## Factoring the root domain

The proof minimizes the following over all necessary allocation summaries:

```
min sum_i max(A[r_i], E[m_i]) + Z_(C-M)[C-1-R]
    where 0 <= m_i <= r_i, R=sum r_i <= C-9, M=sum m_i
```

`factor_bound.py` convolves the three earlier regions into `(M,R)` states. It
keeps the least prior sum for each pair, then adds the corresponding final
table minimum. Every actual schedule supplies one included tuple. Extra
infeasible tuples are favorable relaxations. There is no schedule horizon or
restricted cache policy. Since `M<=R<=C-9`, `C-M>=9`; a fallback cap is not used.

The matching argmins are `r=m=(2,2,3)` at 22 units and `r=m=(2,9,10)` at 36.
Both leave a 15-unit final local problem, whose necessary work is 10,420,224.
The earlier sums are 224,198,656 and 106,758,144 respectively. The actual legal
witnesses attain every one of these owned-work components and have zero charged
work before the cut.

## Capacity saturation

All fourteen local tensors together own 26 units. With the standing immutable
input, **every full local live state and forward-allocation target fits in 27
units**. The backward pattern tracks twelve nodes with total 24 owned units,
so its whole state/allocation domain fits in 25 units. Terminal phase-one live
values plus first output allocation also fit in 27.

All memory comparisons, legal transitions and goals in these finite local
problems are therefore identical for capacities at least 27. Replay proves
these maxima from frozen bytes and clips `C` and `C-M` to 27 only for table
lookup. The global root capacity constraint and `(M,R)` domain retain the
original cap. Node fields and external-entry remapping are checked for all
four blocks, not merely their sizes.

## Audits, controls and limits

Replay builds backward and terminal tables for caps 9 through 27 and demand
tables at 12, 13, 22 and 27. Separate auditors enumerate their forward legal
edges and goals, check Bellman's inequality, and prove every finite distance
has a tight path to a correctly priced goal. Frozen full/local fields, layout,
phases and cost units are bound independently of table checksums. This also
checks unreachable markers. Binary hashes are pinned in `EXPECTED.json`.

Twelve semantic table forgeries are rehashed before auditing: altered distances,
goals, node/input fields, full graph identity, ideal masks, units, phase legality
and cap consistency. Each full witness has separate graph-cost, underclaimed
work, one-below-budget and omitted-regeneration rejection controls. Thirty tiny
algebra cases compare the DP with direct enumeration, including nonmonotone
exact-size prices; three malformed summary inputs are rejected.

The separately authored `direct_enumeration.py` explicitly visits all six
`r_i,m_i` coordinates and reproduces the full prices. Its configuration limit
raises an error instead of returning a result. At 12 units, all **9,178** actual
cache-identity root masks are also checked with uncompressed local values;
their minimum equals the factored 462,716,928. This is a control, not an
exclusion at the original 478,150,656 budget. The 13-unit diagnostic is
396,165,120 against known work 421,494,784, leaving 25,329,664 open; it establishes
no work optimum there.

Source hashes, complete witness hashes and expected values are recorded here
and in the parent source manifest. Table construction limits and direct-check
limits never support an impossibility or optimum claim when reached. This
proof concerns the frozen activation model, not GPU runtime or total training
memory.

## Provenance

Base `a95cc1588fc57a07cfcf5a350206825e6f5b4b52`; master seed
`dafc4be0863b7654352ffb2ba4a4d2df` (the proof is deterministic).
Explicit user-assigned broad frontier research and parent-authorized factored
bound work. Credit Doug Colkitt (@Mister-Meeseeks) for the frozen model,
verifier and predecessor schedules; PR6 for regional composition; same-session
PDB/terminal and common-region-minimum work for reused generators and audits;
and the same-team MLP worker for the constructive allocation witnesses.
The ResNet worker separately authored the six-coordinate checker and reviewed
the mathematical mapping. Codex AI for @0xqtpie authored this follow-up.
Evidence is author-checked only; same-author-team reviews do not constitute
independent scientific validation or maintainer acceptance. Core semantics and
accepted/working records are unchanged. Project code retains its MIT license.
