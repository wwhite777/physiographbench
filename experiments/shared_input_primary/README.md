# Shared-input primary model and training budgets

All four organ modules receive all 16 dynamic values, their observation masks
and five static features. The tuning grid selects only on cohort A validation
root mean squared error (RMSE). Cohort A test and cohort B are evaluation sets.
The no-edge, normalization-retaining, parameter-matched, prescribed-edge and
fixed-random-graph arms share the selected configuration. Longer budgets also
include GRU-D (a gated recurrent unit model with decay for missing measurements).

From the repository root:

```bash
bash experiments/shared_input_primary/run_host_e2.sh --dry-run
PHYSIOGRAPH_NO_TRAINING=1 python3 -B -m unittest discover -s experiments/shared_input_primary/tests -v
```

The plan prints **70 commands: 6 grid cells, 40 arm fits and 24 budget fits**.
To execute the plan after preparing `data/cinc2019_cohort.npz` using the top-level
data instructions, omit `--dry-run`. Outputs default to a fresh `runs/host/`
directory below this experiment; `--output-root` can select another fresh
directory below it. The original records remain under `artifacts/host/`.
No checkpoint, patient error array or patient-level prediction array is bundled.

Expected selection: learning rate **0.001**, large width, validation RMSE
**0.766727** for grid seed 0. The selected no-edge arm's four-seed A-test/B means
are **0.755929 / 0.808817**. The 70 archived `run.json` files preserve all recorded
numbers, training curves, per-organ scores and validation decisions. Read
[E2_E4_READING.md](artifacts/host/E2_E4_READING.md) and
[e2_e4_summary.json](artifacts/host/e2_e4_summary.json) for paired contrasts,
normalization and capacity qualifications, all graph draws and 35/70/105-epoch
budget comparisons. Four training seeds describe fit variation conditional on
the cohort; they do not provide four independent patient populations.

The test suite includes optional fitting checks. `PHYSIOGRAPH_NO_TRAINING=1`
skips those two tests explicitly; the remaining checks cover model inputs,
initialization, graphs, selection, pooling and launcher guards without fitting.
