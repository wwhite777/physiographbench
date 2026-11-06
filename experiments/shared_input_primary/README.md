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

## v5 findings

This separately retuned shared-input series is the primary organ comparison.
The 35-epoch shared no-edge minus GRU-D gaps are **+0.0101 [+0.0072, +0.0130]**
on A and **+0.0029 [+0.0003, +0.0056]** on B (95% paired t confidence intervals,
four paired seeds, 4/4 positive on each cohort). Admissible-edge RMSE is
**0.7551 / 0.8093**, with gaps **+0.0093 [+0.0053, +0.0132]** /
**+0.0034 [−0.0005, +0.0073]** versus GRU-D.

No edge set is consistently better than raw none on this primary backbone.
Admissible minus none is **−0.0009 [−0.0062, +0.0045]** on A and
**+0.0005 [−0.0042, +0.0051]** on B. Except dense-on-B, edge-versus-none
intervals include zero; all random-versus-admissible intervals include zero.
Normalization-retaining none costs **+0.0026 [+0.0008, +0.0043]** on A
(**+0.0008** B); parameter-matched none changes error by **+0.0004 / −0.0003**.
The raw-none contrast therefore includes normalization and message-capacity
changes. Every edge set raises mean renal error (A **0.698 → 0.728–0.741**),
while all arm means beat renal persistence. These are not equivalence tests.

Report longer budgets separately from the 35-epoch primary table. At 70 epochs,
none reaches **0.7496 / 0.8070**, and its gap versus same-cap GRU-D falls to
**+0.0007 [−0.0030, +0.0044] / −0.0026 [−0.0088, +0.0036]**. Narrowing is
**0.0095 / 0.0055**, in 4/4 seeds: the remaining gap is largely a training
budget effect for none. Admissible edges do not close it (**+0.0088 / +0.0053**
at 70; **+0.0120 / +0.0126** at 105). Both organ models worsen at 105, when
validation early stopping fires in 4/4 seeds. Cap changes also alter the cosine
schedule, so longer training does not guarantee lower error.

The earlier [renal input diagnostic](../../diagnostics/renal_shared_input/)
and [fixed-configuration edge diagnostic](../../diagnostics/shared_input_edges/)
are post-hoc controls at the partitioned-backbone-selected configuration. Their
four-seed numbers and capacity qualifications remain separate from this retuned
primary series; they are not ranked against its baseline table.

The test suite includes optional fitting checks. `PHYSIOGRAPH_NO_TRAINING=1`
skips those two tests explicitly; the remaining checks cover model inputs,
initialization, graphs, selection, pooling and launcher guards without fitting.
