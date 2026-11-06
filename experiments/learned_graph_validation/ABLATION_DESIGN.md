# learned-graph experiment — fixed variable-graph ablation design

The host grid has **2 models × 3 graph replacements × 4 seeds = 24 training
commands**. Each command trains only on frozen CinC-2019 A-train, selects on
A-validation and reports both A-test and external B. There are 48 evaluated
model/graph/seed/cohort combinations, not 48 separate fits. No ablation grid fit
was executed by the worker; tests use synthetic data only.

## Fixed graphs

`src/organ_graph_ssm_model.py:ADMISSIBLE_EDGES` is the source of the physiological
directed edges. Organ order and variable slices are cardiovascular `[0,4)`,
pulmonary `[4,8)`, renal `[8,11)`, metabolic `[11,16)`, as in the frozen loader.
An organ arrow `source -> receiver` expands to all source-variable to
receiver-variable pairs. All within-organ pairs and all variable self loops
are retained, making a variable graph without empty receiver neighborhoods.
The runner checks the input feature names and slices before fitting.

All matrices use **A[receiver, source]** and row normalization. The random arm
keeps the physiological graph's exact incoming degree for every receiving
variable and retains self loops; it samples its other source variables without
replacement with NumPy `default_rng(seed)`. Thus it matches density without
forcing the same organ structure. The complete arm contains every ordered
variable pair including the diagonal. The model and random-graph seeds are
0, 1, 2, 3. Graph construction uses a private NumPy generator and does not alter
paired PyTorch initialization. Exact support/weights are saved in each run JSON
and weights are registered buffers included in the checkpoint.

## t-PatchGNN substitution

Reuse `historical_experiment/tpatchgnn_adapter.py`, including patch encoding,
within-variable temporal Transformers, graph polynomial/hop projections and
forecast head. Replace the adaptive adjacency call at each block with the
fixed row-normalized matrix, broadcast over patients and patches. There is no
softmax applied to the zeros and no surviving off-support graph weight.
The existing `A @ H` orientation is preserved. Inherent embeddings and adaptive
gates/dynamic projections are bypassed and frozen, not represented as trained
graph learners. All other modules train normally. Total parameter count remains
357,682; parameters with `requires_grad=True` are recorded separately (355,912).

Architecture source: the existing `EQUATION_MAP.md`, published-settings section,
and local adapter: patch/stride 8 h, width 64, time/graph embeddings 10, one
attention head, one Transformer layer (feed-forward width 2048, dropout .1),
one graph hop, one intra/inter block, and three-layer filter/query MLPs. Empty
patch representation, graph direction and all other existing declared choices
remain inherited; this is not a new published-score claim.

## GraFITi substitution and structural qualification

GraFITi has a sparsity-structure **bipartite channel/time graph**, with learned
attention on observed/query incidence; it has no learned 16×16 channel
adjacency tensor to replace. Multiplying its bipartite edge mask by a variable
adjacency would have incompatible semantics. Merely adding a channel graph
would leave shared time nodes as an unrestricted bypass.

The delivered fixed-graph variant therefore keeps one time state **per
receiving variable**. At each layer, that receiver's time state aggregates
`[source-channel, source-edge]` projected values with the prescribed
`A[receiver,source]`, renormalized over sources present at that time. No source
available gives a zero message. The receiving channel retains its original
learned attention over its own `[receiver-time, edge]` temporal incident pairs.
The edge update uses its receiving channel, its receiving time state and its
old edge; all three updates use the old layer states synchronously.

This removes adaptive **cross-variable** attention weights while preserving
learned temporal attention, value/output/feed-forward projections, raw-query
residuals, the scalar transition and final query-edge readout. Query/key maps
remain active in temporal attention before the final layer. All original 43,400
parameters retain `requires_grad=True`; as in the inherited synchronous adapter,
the final layer's next-node states are not read by its edge-only forecast, so
that last node-attention module has no forecast gradient. This existing issue
is not changed or hidden in the parameter counts. A complete fixed graph produces identical time copies and is
equivalent to the original v3 adapter with only its source-channel-to-time
attention replaced by uniform weights; the independent test oracle verifies
that equality. Identity-graph tests prove there is no residual cross-channel
data path through shared time nodes. Multi-layer paths along allowed graph
arrows remain possible and intentional.

This GraFITi arm is a **declared receiver-conditioned incidence ablation**,
which changes the shared-time representation to make a directed variable
prior meaningful. It cannot be described as swapping a native GraFITi variable
adjacency tensor. Replicated time states also increase memory relative to the
original port; efficient contractions avoid materializing a receiver × source
× width tensor. The project lead should retain this qualification when discussing
what the ablation demonstrates.

## CinC settings and common training budget

The phrase “paper settings” refers to each inherited model's architecture;
the clinical training protocol remains the existing paper comparison on
CinC-2019, not an attempt to run either paper's original dataset protocol.
Sources are `historical_experiment/cinc_port_runner_v3.py`,
`historical_experiment/cinc_port_runner_tp.py`, their equation/fidelity notes,
the learned-baseline LINEAGE, and `src/physiograph_data_loader.py`.

| Setting | Value/source retained |
| --- | --- |
| Input/cohorts | `data/cinc2019_cohort.npz`; frozen A train/val/test, external B; no B fitting or selection |
| Variables/window | Existing 16 named variables; context 12 h, forecast 12 h |
| Normalization | Frozen A-train means/stds, including validation and both test cohorts |
| GraFITi architecture | v3 64 / 4 heads / 2 layers, LeakyReLU(.1), scalar transition, fixed time scale 24 |
| t-PatchGNN architecture | Existing published PhysioNet architecture listed above; CinC context 12 |
| Query graph | Complete future 12 × 16 grid; future labels/masks do not enter either encoder |
| Optimizer | Adam, lr .001, weight decay `1e-5`, default betas/epsilon |
| Maximum epochs | 35, cosine LR schedule with T_max=35 |
| Early stopping | A-validation pooled RMSE, patience 8, minimum improvement `1e-4`; restore best |
| Clipping/batch | Gradient norm cap 1, train/inference batch 128, no dropped final batch |
| GraFITi training loss | Mean observed query error within each nonempty patient, then mean patients (existing v3) |
| t-PatchGNN training loss | Pooled observed-cell MSE (existing t-PatchGNN runner) |
| Reported metrics | Pooled observed-cell MSE/RMSE/MAE for validation, A-test, B; counts included |
| Runtime | CPU default, four threads, workers 0, deterministic seed; optional host CUDA selection |
| Checkpoint/artifacts | Best state dict; full support and weights, active/total parameter counts, input hash, exact command, UTC times, epoch history |

The two models' pre-existing different training losses are deliberately retained;
this is a within-model graph comparison. It is not an optimizer/loss sweep.

## Commands and tests

```bash
bash run_host_e5.sh --dry-run
```

This prints exactly 24 executable commands and performs no training. The same
list is saved in `artifacts/e5_dry_run.txt`. `bash run_host_e5.sh --run` is the
host execution path; the worker has not invoked it. Arguments such as
`--threads 2` and `--device cuda` pass through the enumerator.

`tests/test_e5.py` checks graph direction, forbidden weights, self loops,
random incoming-degree matching/determinism, scalar GraFITi message values and
derivatives, uniform-source complete-graph equivalence, t-PatchGNN polynomial
propagation against explicit sums, bypass of dynamic builders, identity-graph
channel isolation, finite synthetic optimization for all six variants, label
isolation, architecture counts, protocol boundaries and the exact 24-command
enumeration. These are implementation-author checks, not an independent
scientific review.
