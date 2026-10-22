# Factored lower curve for caps 14 through 82

This driver extends the frozen `factored-bound/` necessary-cut theorem to every
integer allocation cap from **14 through 82 units** for `transformer-b4-t128`.
One unit is 131,072 bytes. It produces 69 necessary additional-work prices;
the separately reconstructed constructive curve matches all **67 caps from
16 through 82**. The parent replay verifies every full constructive schedule
before joining the two curves and claiming those fixed-cap work optima.

The two remaining gaps are explicit:

| Cap units | Necessary lower work | Constructive work | Gap |
|---:|---:|---:|---:|
| 14 | 330,104,832 | 355,270,656 | 25,165,824 |
| 15 | 311,984,128 | 312,147,968 | 163,840 |

These gaps are not impossibility results for better constructions. The earlier
11- and 13-unit diagnostics are also retained: 524,877,824 and 396,165,120 lower
work respectively. Their known witnesses use more work. No exact work claim is
made at those diagnostic caps.

These additional memory/work points are research results for the frozen model,
not additional wins on the original fixed benchmark rows. The 22- and 36-unit
suite points are the two results already covered by the parent factored proof.

## Replay and shared audits

From the repository root, standard-library Python:

```sh
python3 research/pdb-cache-round2/curve-bound/joint_replay.py --out /path/to/scratch
```

The joint replay first runs the full `factored-bound/replay.py` table audits
and controls once. It then regenerates and separately audits the additional
output-demand tables, invokes `curve-construction.run`, reconstructs and verifies
all 69 complete schedules, and joins the two curves. The aggregate result is
written to scratch `RESULTS.json`. The lower-only `replay.py` entry point remains
available. No native binary, optional solver, precomputed table or full
action-list collection is committed here.

For the parent replay, `run(repo, out, shared=(table_out, full_result))` accepts
the result returned by `factored-bound.run` in the same replay process. It
checks the complete audit receipt, pinned binary hashes, frozen local fields,
input/output mapping, units and layouts before reuse. The parent can give this
same shared output to `curve-construction.run`, reconstruct all 69 schedules
once, and join verified upper metrics with these lower rows. Generated tables,
receipts and full constructed certificates remain in scratch.

`EXPECTED.json` stores compact lower values, expected constructive prices and
their gaps. A price listed there is not by itself evidence of legal
attainability: that comes from full reconstruction and the unchanged verifier.
The driver result labels its rows as necessary lower bounds.

## Why the same proof covers the curve

The mandatory first-final-GELU cut and common-endpoint region lemma are exactly
those proved in `../factored-bound/README.md`. All first 54 values have been
seen; final UP/GELU occupy eight owned units; the immutable input occupies one;
and the three earlier blocks have no backward completed. Their actual owned
minima last until immediately before the final `norm1` saved-input read.

The exact-size current summary `A[r]`, at-most future-minimum summary `E[m]`,
and forced final-state summary `Z_c[s]` are rebuilt for each required local
capacity. The same exhaustive `(M,R)` convolution includes every actual region
size/minimum tuple. Dropping cache identities and independently selecting
summary minima only weakens a necessary lower bound.

The global cap, current capacity constraint `R<=C-9`, and root final allowance
`C-1-R` retain the actual cap. Only local table lookup clips to 27, because all
fourteen local tensors plus the standing immutable input occupy at most 27
units. Every local state, forward-allocation target and terminal goal already
fits by that capacity; the local transition graphs are therefore identical
above it. The backward pattern saturates no later than 25 units. No assumption
about a restricted checkpoint policy or global action ordering is introduced.

## Validation and scope

The shared proof regenerates and checks backward/terminal caps 9 through 27,
demand caps 12, 13, 22 and 27, all 9,178 twelve-unit root cache identities,
separate six-coordinate enumeration, tiny factoring controls, actual legal
continuations, semantic table forgeries and full-witness forgeries. This
extension adds demand tables at 11 and 14 through 26, excluding the already
audited 22, with full forward-edge Bellman and tight-goal audits. Four more
rehashed table forgeries test overclaim, underclaim, a changed local tensor
size, and cap inconsistency in this additional capacity family.

All 69 values are checked against pinned expectations. The driver checks
monotonicity and the zero-work lower value at cap 82. The parent constructive
replay must separately show the full zero-work schedule there. The bound at
81 units is 163,840, so a verified zero-work 82-unit schedule also identifies
the minimum peak for zero additional work in this model.

Base `a95cc1588fc57a07cfcf5a350206825e6f5b4b52`; master seed
`dafc4be0863b7654352ffb2ba4a4d2df` (deterministic replay). Credit Doug Colkitt
(@Mister-Meeseeks) for the frozen model, verifier and predecessors; prior PR6
and same-session regional/PDB/common-minimum work for the reused proof; the
same-team MLP worker for constructive allocation prices and reconstruction;
and the ResNet worker for independent enumeration and review. Codex AI for
@0xqtpie authored this extension. All evidence is author-checked; same-team
checks are not independent scientific validation or maintainer acceptance.
Core model/verifier and accepted/working records are unchanged. No GPU-memory,
runtime or external-solver claim is made.
