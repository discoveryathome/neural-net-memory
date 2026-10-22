# Closed-label checker author-team review

Read `S/native-proof-checker/check_closed.py` after the parent's full executed
check passed. This receipt is a source-logic review, not another full execution.
It is within the same Codex AI author team, not independent scientific review.

No findings were identified for its pinned transformer cap10 invocation.

- Every block bound is the maximum of that block's missing-closure work,
  12-live-value backward-table work plus disjoint down/residual2 closure work,
  and applicable output-demand-table work. Summing over disjoint block forward
  operations cannot double count. It also dominates the total closure bound
  because every block maximum includes its own share.
- All node sizes are1 or4 allocation units and a valid source state fits10 units.
  An allocation deficit is therefore1..4. Every inclusion-minimal adequate
  eviction is either one four-unit value or exactly the deficit's count of
  one-unit values. Any mixed set containing a four-unit value, multiple
  four-unit values, or excess unit values is nonminimal. The independent
  classifier therefore matches the complete reduced transition relation.
- The raw allocated live set is explicitly checked against the cap before
  normalization can execute backwards or delete values. Dependency values are
  excluded from the eviction candidates.
- Label costs need not themselves be proven minimum-cost reachability values.
  Seeds have labels no greater than zero; every covered transition has a target
  label no greater than source label plus exact transition cost. Inductively a
  mapped real continuation is covered at a label no greater than its true cost.
  Pruning an uncovered transition at this optimistic cost is a stronger check
  than pruning at actual cost. Empty-goal exclusion and closure therefore suffice.
- The checker derives dependencies, saved reads, children, sizes, costs and all
 39 seeds from the frozen graph, validates all input rows, and rejects restricted
  demand mode. All nodes of this pinned graph are recomputable, so omitting a
  separate non-recomputable forward filter loses no needed distinction.
- Needs closure uses a descending topological pass; ready backwards use a
  separate repeated fixed point. These differ structurally from the native code's
  closure loops and single reverse pass while producing the same normalization.

This finite-state closure certificate still depends on the separately reviewed
mandatory-event reduction, lazy inclusion-minimal evictions, eager-backward
normalization, and the exact/admissible table contents. The checker documents
that proof boundary; it is not a claim that all arbitrary fixed-order searches
are global proofs. The package's Bellman auditors and pinned sources are needed
to establish table validity rather than trusting a metadata hash alone.
