# Renal shared-input diagnostic

This post-hoc diagnostic accompanies the renal analysis in the accompanying
paper (Appendix A.12 and Table 14). It asks whether giving every organ node
access to all dynamic inputs reduces renal forecasting error. It is a
one-factor comparison at a fixed configuration, with four paired seeds (0–3).
It does not select or retune a model using test scores.

Both arms use PhysioGraph-GRU with **no graph edges**, four organ-specific
output heads, the same static inputs, and the same forecast boundary and mask
rules. In the partitioned arm, organ nodes see 4/4/3/5 dynamic variables and
their corresponding observation masks. In the shared arm, each node sees all
16 variables and all 16 masks. Both context and forecast-step projections are
widened; recurrent inputs retain model width 96. Shared forecast feedback
therefore carries preceding predictions from every organ. For paired seeds,
the recurrent and output-head initial weights agree; the widened projections
receive fresh initial weights.

The frozen configuration is learning rate 0.0005, width `large`, model width
96, state width 48, two layers, and dropout 0.1. A 12-hour context predicts the
next 12 hours. Each fit uses Adam with weight decay 0.00001, a cosine learning
rate schedule, gradient clipping at 1.0, a 35-epoch cap, patience 8, and minimum
validation improvement 0.0001. Validation error selects the checkpoint.
The configuration is read from the bundled
[`results/v4/selection.json`](../../results/v4/selection.json), with its
distributed fingerprint checked before fitting. The source checks use this
checkout's `src/` modules through the common `release_paths.py` bootstrap.

## Expected saved results

Root mean squared error (RMSE) pools squared normalized prediction errors
over observed target entries across stays, all 12 forecast hours, and the
named organ's variables. A denotes the internal A-test split; B denotes the
external hospital. Units are standard deviations estimated from A-training
data. All-organ RMSE pools all observed targets, rather than averaging organ
RMSEs. The table averages the four per-run RMSEs in each arm.

| Split | Target | Partitioned mean | Shared mean | Shared minus partitioned |
|---|---|---:|---:|---:|
| A | Cardiovascular | 0.699065 | 0.695820 | -0.003245 |
| A | Pulmonary | 0.842647 | 0.835142 | -0.007504 |
| A | Renal | 0.846332 | 0.712003 | -0.134330 |
| A | Metabolic | 0.863499 | 0.818654 | -0.044846 |
| A | All-organ pooled | 0.772360 | 0.757969 | -0.014391 |
| B | Cardiovascular | 0.798902 | 0.797862 | -0.001040 |
| B | Pulmonary | 0.818138 | 0.814637 | -0.003501 |
| B | Renal | 1.067043 | 0.939610 | -0.127433 |
| B | Metabolic | 0.859710 | 0.831859 | -0.027851 |
| B | All-organ pooled | 0.818781 | 0.810142 | -0.008639 |

Differences are computed before rounding. Renal RMSE decreases in all four
paired seeds on both splits. All eight saved fits completed 35 epochs and
are included. Shared inputs add 18,432 projection parameters (759,952 to
778,384); this control does not distinguish input access from the added
projection capacity. Four-seed variation is not a patient-sampling interval.
The results do not establish that input partitioning is the sole cause of
the deficit, resolve the admissible-edge architecture, or explain the
separate CinC-2012 seed behavior. Optimization, forecast boundary handling,
and missingness representation remain alternatives. No clinical utility or
causal physiological interpretation follows from this diagnostic.

[`SHARED_INPUT_READING.md`](SHARED_INPUT_READING.md) gives the per-run scores,
paired signs, seed spans, and persistence comparisons.
[`shared_input_summary.json`](shared_input_summary.json) retains unrounded
values and source fields. The eight archived `run.json` and `curve.csv`
pairs are under `diagnostics/renal_shared_input/runs/<input_mode>/seed<k>/`.
The historical checkpoint replay, its strata, and its implementation reading
are in [`renal_diagnosis.json`](renal_diagnosis.json) and
[`RENAL_DIAGNOSIS.md`](RENAL_DIAGNOSIS.md). That report predates the shared-input
fits; the subsequent reading above reports their completed results.

## Rerun from the repository root

Use the existing environment described by [`requirements.txt`](../../requirements.txt).
Plan inspection and the CPU tests require no patient data and perform no training:

```bash
python3 -B -m unittest discover -s diagnostics/renal_shared_input/tests -v
bash diagnostics/renal_shared_input/run.sh --dry-run --device cpu
bash diagnostics/renal_shared_input/run.sh --plan --device cuda
python3 -B diagnostics/renal_shared_input/shared_input_variant.py --plan
```

The tests use 64 synthetic stays across the four splits. They check actual
context and rollout widths, exact agreement with the original no-edge model,
paired recurrent/head initialization, access to nonrenal inputs, agreement
with the shared clinical training loop, the eight commands, and aggregation
of the archived runs. They do not repeat the eight full fits.

For full fits, first rebuild `data/cinc2019_cohort.npz` using the data and
cohort instructions in [`REPRODUCE.md`](../../REPRODUCE.md). Its expected
SHA-256 is `d52d8131323fc7a3838ae4fe523c2edbc02d2daa781de1859e7d184897dfb51f`.
No further selection file or private source tree is required. Then run:

```bash
bash diagnostics/renal_shared_input/run.sh --device cpu
# Alternatively, on a machine with a compatible accelerator:
bash diagnostics/renal_shared_input/run.sh --device cuda
```

The script runs both modes at seeds 0, 1, 2, and 3, each with `--epochs 35`,
batch size 128, and two CPU threads. Set `PYTHON` to choose an interpreter.
`--output-root` chooses a directory within the repository; the default is
`runs/renal_shared_input/`, separate from the bundled archived records.
Existing destinations or logs cause a refusal before fitting. Generated
checkpoints and per-stay error arrays stay in that output directory; none
are bundled. `TMPDIR` chooses private scratch (default `.scratch/` under the
repository), following the rest of the release. Numerical variation across
hardware/software may affect rerun values; the tables describe the saved fits.

The optional `renal_diagnosis.py` replays the original admissible-edge
checkpoints. It requires regenerated selected runs under
`runs/clinical/selected/<model>/seed<k>/` for `grud`, `physiograph_gru`, and
`physiograph`, including `run.json`, `checkpoint.pt`, and `errors_A.npz` /
`errors_B.npz`. The clinical experiment sequence in `REPRODUCE.md` creates
these outputs. Its bundled reference is `results/v4/per_organ_v4.json`.
After those runs exist, replay with:

```bash
python3 -B diagnostics/renal_shared_input/renal_diagnosis.py \
  --selected-root runs/clinical/selected \
  --reference results/v4/per_organ_v4.json \
  --output-dir runs/renal_shared_input_diagnosis
```

That replay checks against the original per-seed scores with tolerance
0.00001; a newly trained run can differ and then fails the reconciliation
explicitly. It is distinct from the no-edge input-scope comparison.

All recorded file locators are relative to the repository root. Locators
under `runs/clinical/` describe generated historical outputs and do not imply
that weights or error arrays are distributed. Original hash fields and
`historical_verification` describe the original bytes before public path and
descriptive-label transformations. The distribution inventory retains these
original fingerprints separately from hashes of current files; verify the
public files using `SHA256SUMS` and `manifests/distribution.json`.
Software follows the repository's [MIT licence](../../LICENSE); upstream data
terms remain as described in the top-level documentation.
