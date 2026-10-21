# A proposed work lower bound at ten chunks

This is an **author-checked mathematical proof proposal** for the unchanged
`transformer-b4-t128` graph and `activation-memory/v1`. The executable checker
reconstructs the finite state classification and integer arithmetic. The global
charging argument below also requires mathematical review; it has not been
translated into a proof assistant or independently reviewed.

Let one chunk be `u =131072` bytes. Each of the four blocks has forward cost
`F =119537664`. Write `C =8388608`. Each Q, K, V, scores and context operation
costs C, and each UP operation costs 4C. All inputs and allocated outputs count,
and an output is allocated before an input can be dropped. Every forward after
that node's first execution counts toward extra work.

**Claim.** Any legal complete schedule with peak at most 10u has extra-forward
work at least

```
6F +32C =985661440.
```

Consequently, at fixed budget 956301312 the minimum peak is 11u =1441792 bytes:
the predecessor's 11-chunk witness attains it with 737935360 extra work. The same
11u lower bound applies at every budget strictly below 985661440. This leaves the
new 13-chunk schedule at budget 478150656 open to a possible 12-chunk improvement.

## 1. The finite production separator

A probability allocation holds scores(4u) and probabilities(4u); a GELU allocation
holds UP(4u) and GELU(4u). Together with immutable x(u), either allocation uses 9u.
At cap 10u it can have at most one additional tensor of size u. Every other tensor
has size u or 4u.

For any production of a block's residual2, take the last probability/GELU forward
among its strict ancestors before that production. Such a barrier exists because
the schedule starts with inputs only. After it, forbid every further barrier in
that ancestor set and relax all other memory and work constraints. Enumerate the
possible extra survivor and compute the full remaining forward closure. An old
copy of residual2 is removed from this initial closure: a DAG output cannot help
produce its own ancestors, and the new forward cannot overwrite an old live copy.

The 820 enumerated cases in `budget-cut.json` give:

| Target production | Only admissible last-barrier states at cap 10u |
|---|---|
| b1_residual2 | x, b1_up, b1_gelu, b1_residual1 |
| b2_residual2 | x, b2_up, b2_gelu, b2_residual1 |
| b3_residual2 | x, b3_up, b3_gelu, b3_residual1 |

Thus each later-block production has a GELU separator that erases **every earlier
block tensor**. Block 0 has four admissible cases because x is its immutable block
input; the proof below allows that exception. Relaxing memory/work after the last
barrier enlarges reachability, so rejecting every other survivor state is a
necessary-condition argument, not a bounded schedule-search failure.

## 2. Three distinct prefix replays

Take the residual2_3 instance supplied to loss and let S3 be its separator. Every
node in blocks 0–2 has already executed to produce residual1_3, but none is live
at S3. Their later executions are charged, including prefetch before loss.

Backward proj3 requires context3. At S3, context3 and all its attention ancestors
are absent. Trace the actual value instances from the context3 read by backward
proj3 through its probabilities, scores, Q, and norm1 inputs. This chain includes
a new residual2_2 production T2 after S3 and before that probabilities3 allocation.
Let S2 be the last ancestor barrier before T2. It follows S3 and has the unique
block2 separator state in the table.

Constructing T2 from the empty earlier prefix requires every operation in
blocks 0–2 once: charge 3F. All charged block0/1 events precede S2 because they feed
residual1_2; block2 attention and UP also precede S2. Its GELU, down and residual2
may occur at or after S2.

At S2 all block0/1 tensors are absent. Backward proj2 eventually requires a new
context2. Follow its probabilities/scores/Q/norm1 instance chain to a new
residual2_1 production T1 after S2. Its separator S1 follows S2 and erases block0.
Charge 2F for the new blocks 0/1 prefix. The block0 events in this group precede S1
because they feed residual1_1.

At S1 no block0 tensor remains. The analogous context1 dependency chain requires
a new residual2_0 production T0, costing another F. Its entire selected prefix
precedes the probabilities1 allocation in that chain.

These charges are disjoint. The first group's block0/1 events precede S2, while
the second group's follow S2. The second group's block0 events precede S1, while
the last group's follow S1. Events after a separator in its current block have
different node IDs from the next, shorter prefix group. Total:6F. These arguments
allow arbitrary prefetch, recomputation and legal forward/backward branch orders.

## 3. Four additional UP operations

For each earlier block i=0,1,2, the descendant probabilities_(i+1) allocation in
the preceding dependency chain follows that block's selected prefix UP. It holds
8u plus x, leaving only u for everything else, so UP_i(4u) cannot survive it.

Backward GELU_i requires UP_i. It occurs after the descendant backward block:
residual2_i backward waits for next-block norm1 and residual1 backward, and norm1
waits for all Q/K/V branches. In particular the descendant's proj/context/probs
backwards precede GELU_i backward. Thus UP_i must execute again after that
probability allocation. Charge one additional 4C for each earlier block. A later
FFN/prefix reconstruction can itself provide this charge; it is not the original
prefix UP instance selected before the descendant probability barrier.

For block3, residual1_3 must persist from S3 to the final residual2_3 production.
It cannot be recreated after being dropped without another ancestor barrier;
this is also the rejected no-survivor closure. Producing the required down 3 while
retaining x, residual1_3, UP3 and GELU3 would allocate 11u. UP3 must therefore be
dropped before that down allocation. Backward GELU3, after loss, requires it again.
Charge another 4C. Every charged UP has already executed, so none is a free first
forward. Total additional UP charge:16C.

## 4. Additional attention operations

For each i=1,2,3, separator Si contains none of Q_i, K_i, V_i, scores_i or
context_i. Backward proj_i needs context_i; backward context_i needs probabilities
and V_i; backward scores_i needs Q_i and K_i. Recreating probabilities requires
scores_i. Hence all five C-cost operations must execute after Si. Conservatively
charge only four of them,4C per block. Their selected prefix instances precede Si,
so these charges do not overlap section 2.

For block0, use the probabilities1 allocation in section 2. It leaves at most one
unit-sized block0 tensor alive. Scores 0 and probabilities0 each occupy 4u and are
absent. All block0 backwards follow the descendant block's backward, so context0,
V 0, Q 0 and K 0 are still needed afterwards, and scores0 must be recreated for
probabilities0. At most one of these five C-cost values survives; charge four
new operations,4C. These follow the entire selected final block0 prefix, so they
do not overlap its F charge.

The attention nodes and UP nodes are distinct. Attention contributes at least 16C
in addition to the prefix and UP charges. Cheap operations and any other repeats
are omitted from the lower bound.

## 5. Arithmetic, scope and falsification

```
prefix repeats:       (3+2+1)*119537664 =717225984
attention plus UP:   4*(4C+4C)          =268435456
minimum extra work:                     985661440
fixed high budget:                      956301312
shortfall:                               29360128
```

The graph uses whole chunks, so exclusion of peak<=10u raises the lower bound to
11u for budgets below the threshold. The existing 11u witness completes the
optimality proposal at 956301312. The 10u auxiliary witness uses 1258192896 extra
work and does not contradict this budget-sensitive bound.

Supporting author checks include all 820 relaxed survivor cases, every relevant
production in the 10u auxiliary witness, an exact 14-node single-block control
(minimum 85032960 extra work at 10u). These finite checks support the argument;
the global conclusion rests on sections 2–4 as well as the local separator lemma.
A legal 10u schedule below 985661440 work would refute this claim. No accepted or
working result record is changed. Independent mathematical review, formal proof
translation, and hardware/autograd model fidelity remain outside this result.
