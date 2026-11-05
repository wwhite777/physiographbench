# Shared-input edge ablation

This post-hoc diagnostic supplies the fixed-configuration, four-paired-seed edge
comparison reported in Table 15 of the accompanying paper. It holds input access
fixed: every organ node receives all 16 dynamic variables, their 16 observation
masks and five static features, during context encoding and forecast feedback.
Four organ-specific output heads remain. A gated recurrent unit (GRU) updates
each node; only the ordered directed edge set changes across six variants.
There are 24 completed fits: no edges, admissible, dense, reversed, random and
misspecified-1, each with seeds 0–3. No configuration was retuned for this study.

The frozen selection is learning rate 0.0005, large width, model dimension 96,
state dimension 48, two layers, context/horizon 12/12, batch 128, Adam with
weight decay 0.00001, cosine scheduling over a 35-epoch cap, gradient clipping
1.0, patience 8 and minimum validation improvement 0.0001. Selection uses
hospital A validation alone; A-test and hospital B are evaluated afterward.
The saved runs record CUDA execution and four threads. The launcher's default
two threads follows the original plan; use `--threads 4` to match saved metadata.

Root mean squared error (RMSE) pools squared errors over observed forecast
entries before taking a square root. Each organ uses its own observed-entry
denominator. Values are in A-train standard deviations. Four-seed means below
average per-run pooled RMSEs; they do not average organ RMSEs.

| Variant | A-test mean | B mean | Parameters |
|---|---:|---:|---:|
| none | 0.757969 | 0.810142 | 778,384 |
| admissible | 0.756250 | 0.810503 | 930,464 |
| dense | 0.755280 | 0.810723 | 1,006,504 |
| reversed | 0.755865 | 0.811600 | 930,464 |
| random | 0.754535 | 0.810466 | 930,464 |
| misspecified-1 | 0.756032 | 0.810617 | 930,464 |

No-edge has the lowest mean on B; random has the lowest mean on A. Every edge
variant raises renal RMSE relative to no-edge in all four paired seeds on both
cohorts. Edge capacity differs by variant. Four seeds and a configuration
selected on the partitioned backbone cannot isolate a physiological prior from
input access, parameter capacity or optimization. This diagnostic does not
establish clinical benefit or a causal effect. The [reading](SHARED_INPUT_EDGES_READING.md)
and [summary JSON](shared_input_edges_summary.json) retain all pooled/organ
scores, seed variation and paired differences at their original precision.

## Rerun from the repository root

Install the repository requirements and rebuild `data/cinc2019_cohort.npz` using
the top-level reproduction instructions and upstream data terms. Patient data,
weights and per-stay error archives are not bundled here. Inspect either device
plan without loading data or starting training:

```bash
bash diagnostics/shared_input_edges/run.sh --device cpu --dry-run
bash diagnostics/shared_input_edges/run.sh --device cuda --threads 4 --dry-run
python3 -B diagnostics/shared_input_edges/shared_input_edge_variant.py --plan
```

The launcher prints 24 relative commands. Set `PYTHON` to choose an interpreter.
To execute the full 24 fits after rebuilding data:

```bash
bash diagnostics/shared_input_edges/run.sh --device cuda --threads 4 --batch 128
```

CPU execution uses `--device cpu`. New outputs go to
`runs/shared_input_edges/<variant>/seed<k>/` with logs under
`runs/shared_input_edges/logs/`. The launcher preflights every destination and
log before running; existing paths are refused, including in dry runs.
`--output-root` selects another directory inside this repository. Archived
`diagnostics/shared_input_edges/runs/` holds only the 24 original `run.json`
and `curve.csv` pairs; generated checkpoint and error-array locators in JSON
describe omitted outputs. The full runner can regenerate them.

Run the synthetic CPU checks from the root:

```bash
python3 -B -m unittest discover -s diagnostics/shared_input_edges/tests -v
```

These tests use 64 synthetic stays, forward inference and saved-result checks.
They perform no training, downloads or patient-data access. They check every
ordered edge list, shared context/feedback inputs, paired no-edge initialization
and predictions, frozen training-loop agreement, launcher preflight and means.

## Frozen edges and optional full records

`EDGE_CHECKS.json` retains all 24 original ordered edge checks and their original
file hashes. The runner pins that bundled file and requires ordered equality
for each variant. Random uses NumPy `default_rng(0)`, independent of training
seed. Dense maps to the model resolver's `full` graph; misspecified-1 removes
`(0,2)` and appends `(1,2)`. The original edge order controls initialization.

The individual historical v4 run records are not distributed. To enable the
additional original full-record hash and identity check, supply their original
bytes at these repository-root-relative locations:

```text
results/v4/selected/physiograph_gru/seed0/run.json
results/v4/variants/physiograph_gru/<variant>/seed0/run.json
```

The first is the admissible arm; the second covers none, dense, reversed, random
and misspecified-1. Seeds 1–3 at matching locations also permit the tests to
check every original full-record hash. When absent, a clear message identifies
the omitted path and the ordered check continues against `EDGE_CHECKS.json`.
A present file with a wrong hash or identity raises an error.

## Determinism and distribution

All four archived shared no-edge seeds reproduce the renal diagnostic's shared
arm exactly for validation RMSE, epoch selection, complete A/B metric
dictionaries, parameter count and split indices. The [renal diagnostic](../renal_shared_input/)
provides those reference runs. Its original files omit device/thread metadata;
matching CUDA-enabled software strings alone does not prove device identity.
Rerunning on different hardware or software can change numerical results.
This package does not independently replay checkpoint tensors or error arrays.

All locators are relative to the repository root. Source identifiers and paths
were relocated for distribution, while every JSON numeric literal, Boolean and
null and every curve CSV remain unchanged. Hash fields in saved records and the
summary describe original bytes. `manifests/distribution.json` separately records
the original and current file hashes and sizes; `SHA256SUMS` checks current
distributed bytes. Original source-hash entries can refer to unshipped reporting
utilities; they are historical provenance, not runnable dependencies.
Software follows the repository's [MIT licence](../../LICENSE).
