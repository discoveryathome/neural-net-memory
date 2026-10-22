# Native v9 author-team cross-review

Reviewed the fixed `macro_search-v9.cpp` source with SHA-256
`09e0a0fcb5aa7ad5672045a662f8ad6165767a7936245ebd22495775b3f31bb3`,
`run_native-v9.py`, the two pattern-table generators, and the exact cap10 input.
This is a Codex AI review within the same author team. It is not external or
independent scientific acceptance.

No correctness finding was identified for this pinned invocation. Its exhausted
domain can exclude the original cap10/budget956301312 row, subject to the
mandatory-event and normalization arguments below. A generic fixed-order result,
a limited run, demand-mode1 run, or omitted-terminal-forward run cannot establish
that conclusion.

## Mandatory event and exact domain

At the first evaluation of `b3_gelu`, all 54 nodes preceding it in the input's
chosen topological order are precisely its ancestor closure, including itself.
They must have been seen, irrespective of actual earlier evaluation order.
`b3_down` and `b3_residual2` are its only unseen descendants; their first-forward
order is forced. No backward can have happened before this event because the
last sink has not first executed and the model requires loss first.

Immediately after allocating GELU, `b3_up` and `b3_gelu` occupy eight allocation
units; immutable `x` occupies one. At cap10, the remaining live set is empty or
one of the 38 previously seen one-unit values. No other four-unit value fits.
The 39 seeds enumerate all these possibilities at zero charged prefix work.
This is a generous continuation domain. It includes actual event states even
when they were reached with charged recomputation. Its initial progress54
encodes only a seen set; it does not impose a historical order on those nodes.

Both terminal first forwards and the actual loss barrier remain present in this
invocation. The separately tested early-backward omission relaxation is feasible
below the target budgets and gives no exclusion.

## Search reductions

Backward execution costs no activation memory, changes no live values, and has
no negative effect on eligibility. Executing a ready backward immediately is
safe. Descending serialized indices form a reverse topological pass, so one pass
also executes newly enabled ancestors. A backward-complete node has every
descendant backward-complete. Since saved reads are restricted by the verifier
to self/ancestors, that node cannot help regenerate a remaining saved read.
Forbidding its forward and dropping values outside the ancestor closure of all
remaining saved reads is therefore safe after loss. No such pruning occurs
before loss.

Drops can be deferred to the next allocation: they cannot enable a forward,
loss, or backward, and retaining values is harmless until another output needs
space. At that allocation only dependencies must survive. Among the values a
reference trace dropped, retain any excess beyond an inclusion-minimal subset
that frees the required deficit. Those retained values can be dropped later.
The source enumerates every inclusion-minimal adequate subset; its
`freed-minimum_item_size < deficit` predicate is equivalent to inclusion
minimality for positive sizes. When no deficit exists it retains everything.
Eager backward normalization and useful-value deletion preserve the resulting
live-superset dominance argument. The new output is charged alongside all
dependencies before normalization, preserving the allocation peak rule.

The state stores live values, seen-prefix progress, and the complete backward
mask. Per-state minimum cost is sufficient. Reopened immutable records preserve
reconstruction and stale records cannot suppress a cheaper label. Queue
priorities use floating point only for order; budget and heuristic pruning use
unsigned integer work. This exhausted run reached neither its record, memory,
nor time limit, and the queue is empty.

## Heuristic mapping and cost partition

The missing-dependency closure charges each missing previously seen value at
most once; any continuation must execute it at least once. Unseen first
evaluations cost zero. The four repeated block templates and all their local
IDs, byte sizes, costs, read lists, and recomputability flags match exactly.

Each local table charges immutable global `x`, gives that block's entry value
for free, and ignores all other blocks' live memory. The projected local memory
is no larger than actual memory. The backward table's 12 live bits are exactly
the ancestor closure of local saved reads, and its projected backward mask is
an ideal. All those 12 nodes have been seen before that table is used. It relaxes
external readiness and loss timing; each remaining local forward has its actual
charged work. The extra closure charge for the two omitted live dimensions
counts distinct forward operations, so it can be added to the 12-node table.

The output-demand table is used only when all 14 nodes have been seen, no local
backward is done, and the next block's norm1 backward is unfinished. That later
backward requires this block's output. Every local node reaches the local output
and the output backward waits for that consumer, so the output demand must be
met before any local backward. Meeting it immediately whenever output is live,
giving the entry value for free, and relaxing other consumers only enlarge the
domain. Table and closure bounds are combined by maxima within a block, then
summed across disjoint block forward operations. There is no cost double count.

The separate integer auditor checks every legal table edge, every finite
state's tight path to a terminal, invalid-memory states, all done ideals, the
exact binary hashes, every input graph row, the table headers, all four template
remaps, and all 39 seeds. Thus the exact table values and their invocation do
not rely merely on trusting generator completion.

## Executed evidence

`replay.py` compiles the copied fixed source in the sandbox and reruns the exact
input with the pinned tables. It reproduces all integer counters and layer
histograms: 637601 records, 419463 states/expansions, 10474740 generated,
480855 heuristic-pruned, queue0, and maximum six completed backwards. Runtime
was 1.09s and native peak RSS about62MB. The separate binary hash differs because
it was compiled at another path; the source and input hashes are pinned.

`audit_mapping.py` validates 24906 finite backward-table states over168468
edges and 3641 finite output-demand states over24366 edges, plus tight terminal
reachability for every finite state.

`differential.py` reuses the parent team's unnormalized arbitrary-drop oracle,
with a fresh random seed and160 graphs. All960 fresh/postloss cap/budget
comparisons match the copied native v9 binary, including nonuniform sizes,
multiple immutable inputs, non-recomputable nodes, arbitrary self/ancestor
saved reads, and arbitrary valid backward ideals. Maximum oracle expansion was
1240 states. This checks native reductions; it is not by itself a transformer
global bound.

Receipts are `replay-receipt.json`, `mapping-audit.json`, and
`native-differential-results.json`. Prototype execution used the session sandbox
profile; compilation and compiler temporary files stayed within this review
directory. No core, graph, accepted record, or other author's source was edited.
