# edge ablation / post-hoc control reproduction note

This is a **post-hoc** edge ablation on the corrected renal diagnostic shared-input organ
backbone, reported in the accompanying paper. It uses the frozen v4 selected
configuration without retuning: learning rate 0.0005, large width, `d_model=96`,
`d_state=48`, two GRU layers, dropout 0.1, context/horizon 12/12, batch 128, Adam
with weight decay 0.00001, cosine schedule over the 35-epoch budget, gradient
clipping 1.0, patience 8 and minimum validation improvement 0.0001. Checkpoint
selection uses A-validation alone; A-test and B are evaluated afterward.

All four organ nodes receive all 16 variables, their 16 observation masks and
five static features during context encoding and forecast feedback. Both input
projection groups therefore have width 37. The four output heads retain organ
slices `(0,4)`, `(4,8)`, `(8,11)`, `(11,16)`. The renal diagnostic's forecast feedback
rules and input assembly/rollout methods are reused directly.

## Frozen graph definitions

Organ indices are 0 cardiovascular, 1 pulmonary, 2 renal and 3 metabolic.
Directed edges below retain the **recorded order**, which also controls message
module initialization and parameter identity.

| Variant | Ordered directed edges | Parameters |
|---|---|---:|
| none | `[]` | 778,384 |
| admissible | `[(0,2),(0,1),(0,3),(1,0),(1,3),(3,0),(2,3),(2,0)]` | 930,464 |
| dense | `[(0,1),(0,2),(0,3),(1,0),(1,2),(1,3),(2,0),(2,1),(2,3),(3,0),(3,1),(3,2)]` | 1,006,504 |
| reversed | `[(2,0),(1,0),(3,0),(0,1),(3,1),(0,3),(3,2),(0,2)]` | 930,464 |
| random | `[(0,1),(0,3),(1,0),(1,2),(2,0),(2,3),(3,1),(3,2)]` | 930,464 |
| misspecified-1 | `[(0,1),(0,3),(1,0),(1,3),(3,0),(2,3),(2,0),(1,2)]` | 930,464 |

`edges_for()` follows the clinical protocol's v4 definition and the frozen source
resolver, then raises an exception unless its ordered output equals the bundled
seed-0 edge-check record. The bundled `EDGE_CHECKS.json` is SHA256-pinned. If an
original full `run.json` is supplied, its byte hash and identity are checked too.
The random graph uses NumPy `default_rng(0)` to select eight of the
twelve directed non-self edges; it stays fixed across training seeds 0–3.
Misspecified-1 removes `(0,2)` and appends `(1,2)`, retaining the other seven
edges in their original order. The dense spec maps to the frozen resolver's
`full` name. No graph is returned without record equality verification.

The admissible records are
`results/v4/selected/physiograph_gru/seed<k>/run.json`: the original v4 ablation
reuses its Table 1 fits for this arm, as defined in the clinical protocol's
`variant_ablation_runner.source_run()`. All other records are
`results/v4/variants/physiograph_gru/<variant>/seed<k>/run.json`. Tests compare
all six ordered lists against every seed's bundled edge-check record, 24 records
total, and also check any supplied original full records. Original run paths,
hashes and edge lists are retained in `diagnostics/shared_input_edges/EDGE_CHECKS.json`.
The complete historical v4 runs are optional and are not distributed. See the
diagnostic README for required paths.


## Reproduction and completed evidence

See [README.md](README.md) for root-relative commands, the completed 24-run means,
paired determinism results, and the distinction between archived outputs and reruns.
All 24 full runs are complete; the public tests use synthetic data and inference only.
