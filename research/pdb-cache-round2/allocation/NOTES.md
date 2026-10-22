# Joint allocation of retained local caches

Two full schedules reduce additional work at unchanged frozen peaks:

| Peak | Prior work | New work | Saved work |
|---:|---:|---:|---:|
| 2,883,584 (22 units) |234,717,184 |234,618,880 |98,304 (0.0419%) |
| 4,718,592 (36 units) |117,211,136 |117,178,368 |32,768 (0.0280%) |

These are secondary work improvements at the original 239,075,328 and
119,537,664 budgets. They introduce no smaller-peak or global work-optimum
claim. The two complete certificates pass the unchanged verifier.

Replay from the repository root:

```sh
python3 -B research/pdb-cache-round2/allocation/allocation_dp.py
python3 -B -m unittest discover -s research/pdb-cache-round2/allocation -p 'test_*.py'
```

The donated session prefixes both commands with its network-denied,
workspace-write-only `sandbox-exec -f SESSION/research.sb` profile. Generated
results stay in the ignored `generated/` directory or the explicit `--out`.
No binary table is committed. This subfolder imports the existing parent
package's `pattern_db.py`; it has no external PR or scratch-file dependency.

Each earlier block retains its output checkpoint and a selected subset of the
12 ancestors of backward saved reads. The down/residual2 outputs are outside
that 12-value closure; the output checkpoint is counted separately. A concrete
late-V first-forward pass preserves that subset and the output. Its peak is
measured at allocation, before subsequent drops, with all dependencies present.

For block `b` let `k` be the total owned cache units selected in earlier blocks.
Those caches and `b` earlier output checkpoints remain outside its local region.
The local cap is therefore `C-b-k`. The local immutable input accounts for the
one-unit global immutable input; the block-entry checkpoint is already among
the separately charged outputs. The exact backward pattern table gives the
work required from each retained mask. Later backward regions have completed
and dropped their owned values before this region begins.

The DP advances blocks 0, 1 and 2, adding the selected mask's units and backward
work. Future regions depend only on the aggregate resident units, so it retains
the minimum-cost path for each total `k`. It then adds a complete final-block
training price at cap `C-3-k`. This priced domain restricts the final local cap
to at least10 units and uses the stated late-V forward-only retention pass.
It does not assert that all possible global schedules have this form.

Replay rebuilds backward tables for caps10–36 with at most200,000 reached states
per table and 30 seconds per query. It reruns complete 14-node training searches
for caps10–22, each limited to500,000 immutable records and 15 seconds; caps22+
have a checked zero-work plan. Pricing has a 120-second aggregate limit.
Any incomplete query raises, and no incomplete price is reported as exact.
The DP has at most24 total-unit states per layer in these two cases.

The chosen last-block cap is15 in both constructions. Its copied exact full
control retains its original metadata. Tight-edge BFS reconstructs each
earlier backward plan from its table; it is separately bounded at200,000 states.
The global constructor counts every retained checkpoint and activation, all
first forwards, loss, and all explicit backward reads. Replay compares complete
action lists and verified metrics with the stored full certificates.

Credit Doug Colkitt (@Mister-Meeseeks) for the frozen model, graph, verifier and
trial schedules; retention-transfer / PR6 and transformer-regions-round2 / PR10
for exact local search, forward-only retention and regional composition; and
the parent PDB-cache package for its exact backward database. The copied
`regional_exact.py` changes only provenance and its nested repository-root
lookup. Codex AI agents developed the allocation DP and checked the resulting
traces. Evidence is from one author team; scientific review and maintainer
acceptance remain pending.
