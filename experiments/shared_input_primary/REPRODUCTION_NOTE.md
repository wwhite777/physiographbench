# shared-input experiment / D-014: shared-input primary model and E4 budget controls

This directory contains the runner, host command list, tests, and bounded CPU
evidence. No full training was performed. The complete host experiment remains
6 grid fits + 40 arm fits + 24 budget fits = **70 fits**. The only real-cohort
fits in this build were eight one-epoch fits, each restricted to 64 total stays.
The selected configuration in the smoke artifacts is a smoke result, not a
scientific selection for the primary model.

## Frozen protocol and inputs

`renal_protocol.py` is a local copy of shared-edge diagnostic's helper with only its workspace
description and scratch path changed. Every function and class definition,
including `make_data`, `collect_errors`, and `metrics`, is verbatim shared-edge diagnostic.
The runner imports this local helper before importing the read-only shared-edge diagnostic and
renal diagnostic extensions. Those extensions therefore reuse shared-input experiment's paths and scratch.
Bytecode writes are disabled. External source files and results are read only;
`INPUT_MANIFEST.json` records their SHA-256 hashes.

The clinical model has four GRU organ nodes per layer, two layers, organ output
dimensions (4, 4, 3, 5), and no treatment controls. Every node receives all 16
dynamic values, all 16 observation masks, and five static features, both in the
12-hour context and in each of the 12 autoregressive forecast steps. The
feedback mask is all ones, as in renal diagnostic/shared-edge diagnostic. Output heads remain organ-specific.
The frozen shared-edge diagnostic construction order, context encoder, and shared-input rollout
are reused directly.

For each split, the pooled root mean squared error (RMSE) is
`sqrt(sum(observed squared errors) / sum(observed target entries))`.
It is not a mean of stay-level or organ-level RMSEs. Prediction/error arithmetic
uses float32; report sums use float64, exactly as `renal_protocol.metrics()`.
Per-organ RMSE uses the same calculation within each frozen organ slice.
Preprocessing, train/validation/test stay splits, normalization statistics,
one-window-per-stay construction, and cohort hash remain frozen. The cohort
SHA-256 is `d52d8131323fc7a3838ae4fe523c2edbc02d2daa781de1859e7d184897dfb51f`.

All fits use Adam, weight decay 1e-5, gradient-norm clipping at 1.0, cosine
annealing over the requested epoch cap, early-stopping patience 8, and
improvement threshold 1e-4. An epoch improves only when its A-validation pooled
RMSE is below the previous best by more than 1e-4. Each fit starts from a fresh
seeded initialization. A-validation chooses the checkpoint. A-test and B are
evaluated after that checkpoint is restored and do not choose configurations,
checkpoints, edge draws, or epoch caps.

## Grid and selection

`--stage grid --lr LR --width WIDTH` fits one shared-input, no-edge cell at seed
0, with a 35-epoch cap for full runs. The grid is the Cartesian product of
learning rates {0.0005, 0.001, 0.002} and these exact v4 width definitions:

| Width | d_hidden (baseline) | d_model (organ nodes) | d_state | Layers |
| --- | ---: | ---: | ---: | ---: |
| small | 128 | 64 | 48 | 2 |
| large | 256 | 96 | 48 | 2 |

`d_state` is retained in the config although the GRU node does not use SSM state
channels. `d_hidden` applies to GRU-D, not the organ GRU nodes.

Grid records live at `OUTPUT/grid/lrLR_WIDTH/seed0/run.json`. After each cell,
the runner checks whether all six records exist. Only then does it create
`OUTPUT/selection_shared.json`, containing the chosen configuration and all six
complete grid records, their paths and hashes. Failed cells remain in that
inventory and are excluded from selection. All failed cells produce a blocked
selection. Missing cells, wrong identities, inconsistent batches/scopes/cohorts
or epoch caps, and an existing selection are rejected.

Selection minimizes A-validation pooled RMSE among complete cells; ties use
lexical configuration ID, exactly as v4. Tests change A-test/B scores and verify
that this choice does not change. Arm runs re-read and verify the selection
against all six run files, and require the same batch and stay cap. A smoke
selection cannot be used for a full run. Grid fits that record a failure return
exit 0 so the other cells can still be inventoried, following the v4 convention;
`run.json.status` and the final selection are authoritative. Arms and budget
fits return exit 1 on a recorded failure.

## Ten arms

`--stage arms --arm ARM --seed S` uses the selected shared-input configuration,
seeds 0–3, and a 35-epoch cap. There is no separate tuning per arm. The arms are
`none`, `none_norm`, `none_pmatch`, `admissible`, `dense`, `reversed`, `random_s0`,
`random_s1`, `random_s2`, and `misspecified-1`.

Organ indices are 0 cardiovascular, 1 pulmonary, 2 renal, and 3 metabolic.
The ordered admissible edges are
`[(0,2),(0,1),(0,3),(1,0),(1,3),(3,0),(2,3),(2,0)]`.
Dense uses all 12 directed non-self edges in source/target order; reversed
flips each admissible pair in place. `misspecified-1` removes (0,2) and appends
(1,2). The runner checks ordered equality against pinned v4 seed-0 records
before returning these sets. Tests and `EDGE_CHECKS.json` additionally check all
four frozen training-seed records for all six original variants (24 records).

The random draws sample eight of the 12 directed non-self pairs without
replacement using NumPy `default_rng(draw_seed)`, sort the sampled indices,
and retain the frozen dense ordering. The draw seed is independent of the
training seed. `random_s0` exactly equals v4/shared-edge diagnostic's original random graph.
No draw was rejected or chosen using a model score.

| Arm | Ordered edges | Intersection / union with admissible | Jaccard |
| --- | --- | --- | ---: |
| random_s0 | (0,1), (0,3), (1,0), (1,2), (2,0), (2,3), (3,1), (3,2) | 5 / 11 | 0.45454545454545453 |
| random_s1 | (0,1), (0,2), (0,3), (1,0), (1,3), (2,1), (3,0), (3,2) | 6 / 10 | 0.6 |
| random_s2 | (0,1), (0,2), (0,3), (1,0), (1,2), (2,3), (3,1), (3,2) | 5 / 11 | 0.45454545454545453 |

Jaccard overlap means intersection size divided by union size. These random
controls overlap substantially with the prior: two sets of eight edges drawn
from only 12 possible edges must share at least four. Treat them as overlapping
controls rather than disjoint alternatives. Each run prints its edge list,
draw seed, overlap, parameter count, and capacity rule when applicable.

### `none_norm`: empty edges with coupling LayerNorm

The frozen empty-edge coupling returns the hidden state unchanged, even though
its LayerNorm parameters exist. `none_norm` wraps each such coupling, keeps its
original LayerNorm module, and has empty message and gate module lists. Its
forward code is exactly the simulator `_MatchedCoupling` empty-edge operation:

```python
return self.norm(hidden), hidden.new_zeros(hidden.shape[0], 0)
```

Thus the summed message is zero, LayerNorm receives `hidden + 0`, and the
returned gates have shape `(batch, 0)`. The implementation is
`NormalisationRetainingCoupling` in `shared_input_primary.py`. Tests compare
the return expression with the simulator source, inspect the norm input,
verify the norm parameters and gradients, and verify that raw `none` bypasses
the operation. The total parameter count equals `none` because its norm
parameters already exist; those parameters become active in `none_norm`.

### `none_pmatch`: exact capacity match by widened input projections

Recurrent dimensions, depth, organ heads, and empty coupling behavior stay at
the selected config. Each of the eight shared-input projections (four context,
then four feedback) is widened by an active nonlinear branch:

```text
base(x) + down(GELU(up(x) + partial_bias))
```

`base` is the original 37-to-d linear projection. `up` is a bias-free 37-to-h
map; `down` is a bias-free h-to-d map. The first b hidden units have learned
biases; the others have fixed zero bias. There are no padding parameters or
unused widening parameters. This control changes projection capacity and
nonlinearity; matching parameter counts does not imply equal computation or
identical function classes.

For recurrent width d, two layers L, eight admissible edges E, and input p=37:

```text
delta = E * L * (d*d + 3*d + 1)
H = ceil(delta / (p + d + 1))
b = delta - H * (p + d)
```

The `d*d + 3*d + 1` term is one message linear map including bias plus one
scalar gate linear map including bias. H and b are independently distributed
over the eight projections by quotient and remainder, giving earlier
projections one extra unit/bias where needed. Added parameters are exactly
`H*(p+d)+b = delta`. `widen_projections` records the rule, widths, biases,
base count, target count, and achieved count in every `none_pmatch` run.

| Width | `none` / `none_norm` | `admissible` / `none_pmatch` | Added | Hidden widths, context then feedback | Learned hidden biases |
| --- | ---: | ---: | ---: | --- | --- |
| small | 355,088 | 423,712 | 68,624 | 85,84,84,84,84,84,84,84 | 82,82,82,81,81,81,81,81 |
| large | 778,384 | 930,464 | 152,080 | 142,142,142,142,142,142,142,141 | 141,141,141,141,141,140,140,140 |

Counts include all parameters, including the inherited dormant empty-coupling
norm parameters in `none` and `none_pmatch` (256 small / 384 large). Tests
verify equality with the actual admissible model at both widths and nonzero,
finite gradients for every added projection parameter.

### Equality with shared-edge diagnostic

**The `none` arm reproduces shared-edge diagnostic's shared-input `none`.** If the new full-grid
selection is v4's learning rate 0.0005 and large width, the same seed, cohort,
batch, device, threads, 35-epoch cap, and runtime are expected to give exactly
the same fit and predictions as shared-edge diagnostic. Tests establish bitwise-equal initialized
state dictionaries and evaluation/training forward outputs for both widths
and all four seeds, including dropout under a reset RNG. No full-fit equality
claim was empirically tested in this build. `none_norm` changes the empty-edge
forward operation; `none_pmatch` changes the projections. Neither is the shared-edge diagnostic
`none` reproduction. Pairing training seeds across edge arms retains shared-edge diagnostic's
construction order; it does not assert identical shared initial weights across
different edge counts.

## E4 budget stage

`--stage budget --model {none,admissible,grud} --epochs {70,105} --seed S`
fits three models at each cap for seeds 0–3: 24 fits. `none` and `admissible`
read the selected shared-input config. GRU-D reads only its frozen v4 selection:
learning rate 0.0005, large width, d_hidden=256, and 449,568 parameters. Its
frozen baseline class is imported through `physiograph_training_runner.build_any`.
The launcher's common `--selection` argument is ignored for GRU-D; that model
always resolves the pinned v4 selection file.

Each budget run is a fresh fit, with cosine `T_max` set to 70 or 105. It is not
a checkpoint continuation. Patience 8 and min_delta 1e-4 remain in effect, so
the larger cap does not force every fit to train for 70/105 epochs. Both caps
are reported separately; B never selects between them. Synthetic control-flow
tests verify both cosine periods, patience, threshold, and delayed test use.

## Outputs and host use

Every attempted fit writes `run.json` with its status/failure, config, seed,
edges, n_params, completed epochs, best epoch, complete training curve,
validation selection metric, and pooled/per-organ metrics on `A_validation`,
`A` (A-test), and `B`. Failed fits retain null unavailable metrics. The CSV curve,
best checkpoint, and per-stay error arrays for all three evaluation splits are
saved alongside it. Source hashes, cohort/split metadata, and selection
provenance accompany each run. `retuned` denotes use of the retuned shared
backbone configuration; it does not mean arm-specific hyperparameter tuning.

The host launcher accepts `--device cpu|cuda`, `--threads`, `--batch`,
`--output-root`, and `--dry-run`. It prints or executes GRID first, then ARMS,
then BUDGET; the last grid cell creates the selection before ARMS starts.
It preflights all 70 run directories, all logs, and the selection before any
fit or directory creation; existing destinations, including dangling symlinks,
are refused. Output paths must stay below this task directory. Dry-run creates
no output directories and needs no pre-existing selection. Logs live below the
chosen output root. `CUBLAS_WORKSPACE_CONFIG=:4096:8` is exported, and scratch
is the owner-specified `.research tooling-tmp/shared-input experiment-shared-input-primary-runner-build`.

From this directory, inspect the host command list with:

```bash
bash run_host_e2.sh --device cpu --threads 2 --batch 128 --output-root "$PWD/artifacts/host" --dry-run
```

Omit `--dry-run` for the authorized host training run. CUDA is available as a
launcher option but was only dry-run checked here. No GPU fit was performed.
For a bounded integration check, use the existing environment:

```bash
TMPDIR="$PWD/.research tooling-tmp/shared-input experiment-shared-input-primary-runner-build" \
  python3 -B -m unittest discover -s tests -v
```

The smoke test uses six one-epoch grid cells to exercise real selection, one
`none_norm` arm command, and one GRU-D budget-stage command, all with
`--max-stays 64 --epochs 1 --device cpu --threads 2 --batch 16`. Error arrays
recompute the JSON metrics exactly, and all per-organ values are finite.
`SMOKE_RESULTS.json`, `EDGE_CHECKS.json`, `DRY_RUN_CHECKS.json`, the logs, and
`DISTRIBUTION_NOTE.md` contain the measured evidence. The build did not modify scientific
freezes, perform full training, access the network, install dependencies, use
git, write to `/tmp`, or operate on tmux infrastructure.
