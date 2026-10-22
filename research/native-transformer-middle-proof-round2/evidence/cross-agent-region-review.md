# Native v16 incremental author-team review

Reviewed frozen source SHA-256
e3f7cbaabc480e07aca401994618309ed7fd967c52f2b7bae3717451c12c1959
against the previously reviewed v9 transition implementation. The additions are
table loading, last-block terminal phases, and a common-endpoint per-region
occupancy bound. No transition/reduction change was introduced. No correctness
finding was identified for the pinned invocation. This remains review within
one Codex AI author team, not independent scientific review.

## Common occupancy lemma used by this version

Choose the active highest unfinished block. Earlier blocks have no backward
done, and all their first forwards have been seen. Their output reads remain
pending until at least the active norm1 backward saved-input read. For each
earlier owner region choose the minimum number of owned resident allocation
units over the interval from the current state through that read. Each minimum
is no greater than its current owned units and is attained before any local
backward or external output read.

At its minimum state the owner's future work is at least E(m), the minimum
ordinary cap12 output-demand-table value among local live states of at most m
owned units. Its whole future owned work is also at least its ordinary current
bound. Taking their maximum is valid. All minima reserve their summed physical
bytes at every active-block operation, despite identity transfers, so the active
local terminal/backward projection fits cap12 minus their sum. Cost owners are
disjoint. Every real continuation has an enumerated vector of minima, hence the
minimum over vectors is a necessary bound.

The boundary is the active norm1 saved-value read, before any post-read drop.
Backward allocates and consumes no activations, so including its zero-cost
completion in the local table changes no allocation peak. Earlier input values
remain freely available in each local projection; the standing allocation
charges the actual global immutable x.

## Source implementation checks

- Region E is built from exact owned byte counts and then prefix-minimized, so
  E[m] covers every live mask with owned bytes at most m. The standing immutable
  input is excluded from those owned counts.
- The min-convolution enumerates every integer minimum0..currentownedunits.
  It keeps only reserved totals below12. Any actual vector has sum at most
  current earlier-owned units, which is at most11 under the cap, so this drops
  no actual possibility.
- Each owner contribution is max(its already-admissible block bound,E[m]).
  Dynamic programming adds only disjoint owners' forward work.
- Requested reduced caps9..12 select the corresponding exact table. Requests
  below9 use cap9, a more generous capacity. This safely retains later-state
  partitions rather than omitting unavailable capacities.
- The active table uses the actual local backward mask after loss, or the
  exact first-down terminal phase before loss. Guards require all its first12
  values seen and its output still unseen for a preloss terminal projection.
- The region guard requires all earlier forwards seen and no earlier backward.
  Completed later blocks contribute their existing admissible zero bounds.
  Active block0 uses the unchanged ordinary bound.
- Budget+1 sentinels and discarding DP labels above budget cannot discard a
  continuation of cost at most budget. All work arithmetic is integral.
- The exporter validates every lower-cap table's full/local graph identity,
  units, row widths, done ideals, live names, terminal phases, backward-table
  link, and binary hash.

The proof uses the common-endpoint heuristic, not the subsequently explored
nested-own-read variant. Its initial minimum is462,716,928. The separate
binary/common profile and nested profile prices agree pointwise between two
implementations over all9178 critical-cut seeds. The original cut retains both
terminal first forwards and the loss barrier; no omitted-terminal relaxation
is used here.

## Executed checks

Separate copied-source compile/replay reproduced every integer search counter
and layer:1274821 records,1002736 states/expansions,82502307 generated,
61657976 pruned, queue0, maximum29 completed backwards. Runtime21.13s and peak
native RSS190.7MB. The source, input, binary and all arguments are pinned in
v16/replay-receipt.json.

The new generic stress test covers240 seeded2/3-block graphs with two operators
per block, nonuniform bytes/costs, random ancestor/self/empty saved reads, random
valid partial backward suffixes and live masks. It builds89648 independent
local-table entries across every cap1..C/live mask/done ideal, checks both common
and nested bounds against unreduced global Dijkstra, and checks834 actual
partition owned-cost inequalities on shortest traces. All240 tails pass the
unchanged full verifier after explicit unrestricted initialization; only their
tail memory is capped. Maximum global oracle318 states; total runtime0.39s.
See ../test_generic_region_bounds.py/.json/.log.

The 44 guarded states of the known legal12u trace also satisfy the table-based
common and nested bounds against exact remaining work. Earlier v9 normalization
and lazy-drop controls remain applicable because the transition implementation
is unchanged.

These checks support the mathematical reduction and heuristic. A separately
authored full closed-label checker is still needed to remove reliance on native
queue/hash behavior for the final computational certificate.
