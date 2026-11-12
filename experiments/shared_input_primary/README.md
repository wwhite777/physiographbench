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
**0.0095 / 0.0055** (from +0.0101 / +0.0029 at 35 epochs), in 4/4 seeds. It has
two parts: none improves (A 0.7559 → 0.7496, B 0.8088 → 0.8070) and same-cap
GRU-D worsens (A 0.7458 → 0.7489, B 0.8059 → 0.8096); on B the GRU-D change is
the larger part. Cap, cosine schedule and early stopping change together, so
this is a sensitivity to those choices, not an isolated attribution to
training duration. Admissible edges do not close the gap (**+0.0088 / +0.0053**
at 70; **+0.0120 / +0.0126** at 105). Both organ models worsen at 105, when
validation early stopping fires in 4/4 seeds; a longer cap does not guarantee
lower error.

The earlier [renal input diagnostic](../../diagnostics/renal_shared_input/)
and [fixed-configuration edge diagnostic](../../diagnostics/shared_input_edges/)
are post-hoc controls at the partitioned-backbone-selected configuration. Their
four-seed numbers and capacity qualifications remain separate from this retuned
primary series; they are not ranked against its baseline table.

The test suite includes optional fitting checks. `PHYSIOGRAPH_NO_TRAINING=1`
skips those two tests explicitly; the remaining checks cover model inputs,
initialization, graphs, selection, pooling and launcher guards without fitting.

## Ten-seed selected-cap extension

Version 1.3.0 holds the original four-seed A-validation cap choices fixed:
none=105, admissible=70, GRU-D=35. Seeds 4–9 add 18 fits; together with the
original records they supply ten paired seeds for each selected family.
Admissible − none is +0.0007 [−0.0018, +0.0032] A and +0.0037 [+0.0012,
+0.0061] B. None − GRU-D is +0.0094 [+0.0074, +0.0115] A and +0.0052
[+0.0027, +0.0078] B. There is no edge benefit at the selected caps, and the
organ model trails GRU-D. The four-seed matched-cap sensitivities remain above.
Caps and cosine schedules differ jointly; these are selected-procedure contrasts.
Intervals conditional on fixed cohorts do not establish equivalence.

```bash
python3 -B experiments/shared_input_primary/read_n2.py
python3 -B experiments/shared_input_primary/n2_host.py --dry-run
```

Rebuild and verify the 2019 cohort, and generate the original four-seed series
with `run_host_e2.sh --execute` before an extension training run. The new planner
prints 18 commands and `--execute` runs them sequentially. Each writes under
`experiments/shared_input_primary/runs/ten_seed/FAMILY/seedN/`; use the existing
35/70/105 primary launcher for seeds 0–3. Full training follows the original
family-specific optimizer, batch, stopping and cosine period. A small CPU smoke
requires explicit `--smoke` on `n2_train.py` and stays outside the frozen results.

Only `run.json` is distributed for new fits. `read_n2.py` checks all selected-cap
record hashes, identities and stopping fields before printing four/ten-seed paired
intervals, sign counts and minimum detectable differences at 80% power. It does
not claim to replay the omitted new weights, CSV curves or per-stay error arrays.
