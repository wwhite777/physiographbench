# E1 reading of the registered positive control

**REGISTERED VERDICT: PASS.** All three κ = 1 comparator intervals are positive, each comparator’s mean gap is non-decreasing across the registered κ grid, and the pre-neural oracle qualification passes.

Prepared under positive-control reading by research tooling as research engineer and analysis author. This is a reading of existing fits, not an independent scientific review. No training, retuning, endpoint change, comparator substitution, or trend tolerance was used.

## Endpoint and provenance

The governing text is [DESIGN_E1.md](../../DESIGN_E1.md), “Neural success criterion and future run plan”; its original SHA-256 is preserved in [DESIGN_REGISTRATION.json](../../DESIGN_REGISTRATION.json) and in [oracle_results.json](../../oracle_results.json). The verbatim registered criterion and every reported numerical quantity, at full stored or computed precision, are in [e1_summary.json](e1_summary.json). Tables round continuous values to six decimals only for display; all verdicts use unrounded values.

Normalized root mean squared error (NRMSE) pools squared errors across held-out patients, the 24 forecast samples, and channels within an organ before taking a square root. Divide each organ RMSE by its fixed range and average the three organs equally. The one reference is the dense noisy `truth` array in `datasets/kappa_1.npz`, with dataset seed 0, all 400 patients, and all 73 saved times. Each range is the organ-wide maximum minus minimum plus 0.000001; the cardiovascular range pools its four channels.

| Organ | Fixed range | Source field / operation |
| --- | --- | --- |
| cardiovascular | 140.874940 | `datasets/kappa_1.npz::truth[..., [0, 1, 2, 3]]`, max − min + ε; every fit `reference_ranges.cardiovascular` |
| renal | 2.140162 | `datasets/kappa_1.npz::truth[..., [4]]`, max − min + ε; every fit `reference_ranges.renal` |
| metabolic | 4.154751 | `datasets/kappa_1.npz::truth[..., [5]]`, max − min + ε; every fit `reference_ranges.metabolic` |

Primary values come from each result’s `metrics.macro_nrmse_fixed` and `metrics.organ_nrmse_fixed`. The fields ending in `per_kappa` use each fit’s held-out patients and all saved times as a diagnostic range; they are retained in JSON and never used in the registered tests. Organ RMSE to NRMSE conversion, macro averaging, ranges, dataset/manifest hashes, paired splits, normalization, masks, and seeded graph draws were checked. Saved predictions are unavailable, so residual-level RMSE was not recomputed.

## Registered paired comparisons

For each seed, Δ = comparator macro-NRMSE − admissible macro-NRMSE; positive values favor admissible. The sample standard deviation uses ddof = 1. Each two-sided 95% interval is mean(Δ) ± 3.182446305 × sd(Δ)/√4, with three degrees of freedom. “Signs +/0/−” counts positive, zero, and negative paired gaps. These are four training/split seeds on one generated patient set, not a patient-population uncertainty interval. For each table entry, JSON `primary_comparisons[comparator][κ-index].pairs` identifies both source files and the exact `metrics.macro_nrmse_fixed` fields; `statistics` stores all calculations.

### Comparator: none

| κ | Δ seed 0 | Δ seed 1 | Δ seed 2 | Δ seed 3 | Mean Δ | SD | 95% lower | 95% upper | Signs +/0/− |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.000000 | -0.003844 | -0.007402 | -0.004595 | -0.002751 | -0.004648 | 0.001986 | -0.007808 | -0.001488 | 0/0/4 |
| 0.500000 | 0.002827 | 0.002175 | 0.001463 | 0.003152 | 0.002404 | 0.000748 | 0.001215 | 0.003594 | 4/0/0 |
| 1.000000 | 0.017113 | 0.015824 | 0.014533 | 0.016724 | 0.016048 | 0.001145 | 0.014226 | 0.017871 | 4/0/0 |

### Comparator: reversed

| κ | Δ seed 0 | Δ seed 1 | Δ seed 2 | Δ seed 3 | Mean Δ | SD | 95% lower | 95% upper | Signs +/0/− |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.000000 | -0.003063 | -0.007479 | -0.003946 | -0.002261 | -0.004187 | 0.002300 | -0.007846 | -0.000528 | 0/0/4 |
| 0.500000 | 0.004260 | 0.001858 | 0.002851 | 0.003202 | 0.003043 | 0.000991 | 0.001466 | 0.004620 | 4/0/0 |
| 1.000000 | 0.018248 | 0.014783 | 0.016194 | 0.017746 | 0.016743 | 0.001572 | 0.014242 | 0.019244 | 4/0/0 |

### Comparator: random

| κ | Δ seed 0 | Δ seed 1 | Δ seed 2 | Δ seed 3 | Mean Δ | SD | 95% lower | 95% upper | Signs +/0/− |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.000000 | -0.002367 | -0.006457 | -0.003970 | -0.001605 | -0.003600 | 0.002144 | -0.007012 | -0.000188 | 0/0/4 |
| 0.500000 | 0.003796 | 0.000718 | 0.000301 | 0.002110 | 0.001731 | 0.001579 | -0.000781 | 0.004244 | 4/0/0 |
| 1.000000 | 0.017253 | 0.015489 | 0.004930 | 0.009211 | 0.011721 | 0.005693 | 0.002662 | 0.020779 | 4/0/0 |

### Explicit registered sub-tests

| Comparator | κ = 1 mean > 0 | κ = 1 interval wholly > 0 | κ: 0 → 0.5 mean non-decreasing | κ: 0.5 → 1 mean non-decreasing | Whole trend | Comparator result |
| --- | --- | --- | --- | --- | --- | --- |
| none | PASS | PASS | PASS | PASS | PASS | PASS |
| reversed | PASS | PASS | PASS | PASS | PASS | PASS |
| random | PASS | PASS | PASS | PASS | PASS | PASS |

The exact adjacent mean increments below are descriptive evidence for the strict non-decreasing comparisons; no tolerance is applied.

| Comparator | Mean gap κ = 0 | Mean gap κ = 0.5 | Mean gap κ = 1 | Increment 0 → 0.5 | Increment 0.5 → 1 |
| --- | --- | --- | --- | --- | --- |
| none | -0.004648 | 0.002404 | 0.016048 | 0.007052 | 0.013644 |
| reversed | -0.004187 | 0.003043 | 0.016743 | 0.007230 | 0.013700 |
| random | -0.003600 | 0.001731 | 0.011721 | 0.005331 | 0.009989 |

The additional oracle qualification is part of the registered conjunction. Gains G are relative RMSE reductions, G = 1 − RMSE_source-augmented/RMSE_local. Its target macro averages only renal and metabolic NRMSE, unlike the three-organ neural endpoint.

| κ | Oracle quantity | G | Registered requirement | Result | oracle_results.json field |
| --- | --- | --- | --- | --- | --- |
| 0.000000 | renal | -0.019713 | <= 0.020000 | PASS | `cells[0].per_organ.renal.rmse_relative_reduction` |
| 0.000000 | metabolic | -0.014626 | <= 0.020000 | PASS | `cells[0].per_organ.metabolic.rmse_relative_reduction` |
| 1.000000 | renal | 0.209625 | >= 0.050000 | PASS | `cells[1].per_organ.renal.rmse_relative_reduction` |
| 1.000000 | metabolic | 0.289632 | >= 0.050000 | PASS | `cells[1].per_organ.metabolic.rmse_relative_reduction` |
| 1.000000 | target_macro | 0.250331 | >= 0.050000 | PASS | `cells[1].target_macro_nrmse_fixed.rmse_relative_reduction` |

**Oracle qualification: PASS. Overall registered result: PASS.** No extra positive neural gain is required at κ = 0. Indeed, all primary comparator gaps are negative there: edge use has a cost in the constructed no-coupling cell. At κ = 0.5, the random comparator’s interval includes zero; that cell is still included in the trend test and is not an endpoint requirement.

## Descriptive controls

The following arms are descriptive under the registration. Each paired difference is the named arm minus the stated reference, so negative values favor the named arm. The same seed pairing, sample SD, and t-interval formula are used for description; these intervals are not additional success criteria. Every pair and its source fields are retained in JSON `descriptive_comparisons`.

### Descriptive differences versus admissible

| Arm | κ | Δ seed 0 | Δ seed 1 | Δ seed 2 | Δ seed 3 | Mean Δ | SD | 95% lower | 95% upper | Signs +/0/− |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dense | 0.000000 | 0.000115 | -0.000801 | 0.001101 | 0.002449 | 0.000716 | 0.001392 | -0.001499 | 0.002932 | 3/0/1 |
| dense | 0.500000 | 0.000974 | -0.001692 | 0.002007 | 0.001151 | 0.000610 | 0.001599 | -0.001935 | 0.003155 | 3/0/1 |
| dense | 1.000000 | 0.002944 | 0.000689 | 0.000122 | 0.001002 | 0.001189 | 0.001225 | -0.000760 | 0.003139 | 4/0/0 |
| misspecified-1 | 0.000000 | 0.000844 | -0.003099 | -0.001672 | 0.001608 | -0.000580 | 0.002187 | -0.004060 | 0.002901 | 2/0/2 |
| misspecified-1 | 0.500000 | 0.000316 | -0.000292 | 0.001601 | 0.001994 | 0.000905 | 0.001073 | -0.000802 | 0.002612 | 3/0/1 |
| misspecified-1 | 1.000000 | 0.008376 | 0.007198 | 0.007744 | 0.007217 | 0.007634 | 0.000556 | 0.006749 | 0.008518 | 4/0/0 |
| control_gru | 0.000000 | -0.000804 | -0.004182 | -0.002517 | 0.000702 | -0.001700 | 0.002114 | -0.005063 | 0.001663 | 1/0/3 |
| control_gru | 0.500000 | 0.002233 | -0.000806 | -0.001834 | -0.003026 | -0.000858 | 0.002252 | -0.004441 | 0.002725 | 1/0/3 |
| control_gru | 1.000000 | 0.001801 | -0.001799 | 0.000333 | -0.001014 | -0.000170 | 0.001582 | -0.002687 | 0.002347 | 2/0/2 |
| control_gru_matched | 0.000000 | -0.000185 | -0.000989 | -0.003109 | 0.003410 | -0.000218 | 0.002715 | -0.004538 | 0.004102 | 1/0/3 |
| control_gru_matched | 0.500000 | 0.001329 | 0.001540 | 0.000205 | -0.000666 | 0.000602 | 0.001029 | -0.001035 | 0.002239 | 3/0/1 |
| control_gru_matched | 1.000000 | 0.003002 | 0.000335 | 0.001479 | -0.002982 | 0.000459 | 0.002540 | -0.003584 | 0.004501 | 3/0/1 |

### Descriptive differences versus none

| Arm | κ | Δ seed 0 | Δ seed 1 | Δ seed 2 | Δ seed 3 | Mean Δ | SD | 95% lower | 95% upper | Signs +/0/− |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dense | 0.000000 | 0.003959 | 0.006601 | 0.005696 | 0.005200 | 0.005364 | 0.001102 | 0.003611 | 0.007118 | 4/0/0 |
| dense | 0.500000 | -0.001853 | -0.003866 | 0.000544 | -0.002000 | -0.001794 | 0.001808 | -0.004671 | 0.001083 | 1/0/3 |
| dense | 1.000000 | -0.014168 | -0.015135 | -0.014411 | -0.015722 | -0.014859 | 0.000707 | -0.015984 | -0.013734 | 0/0/4 |
| misspecified-1 | 0.000000 | 0.004688 | 0.004303 | 0.002923 | 0.004359 | 0.004068 | 0.000782 | 0.002824 | 0.005313 | 4/0/0 |
| misspecified-1 | 0.500000 | -0.002511 | -0.002467 | 0.000138 | -0.001157 | -0.001499 | 0.001259 | -0.003503 | 0.000505 | 1/0/3 |
| misspecified-1 | 1.000000 | -0.008736 | -0.008626 | -0.006789 | -0.009507 | -0.008415 | 0.001152 | -0.010248 | -0.006581 | 0/0/4 |
| control_gru | 0.000000 | 0.003040 | 0.003220 | 0.002078 | 0.003453 | 0.002948 | 0.000604 | 0.001987 | 0.003909 | 4/0/0 |
| control_gru | 0.500000 | -0.000594 | -0.002980 | -0.003297 | -0.006178 | -0.003263 | 0.002288 | -0.006903 | 0.000378 | 0/0/4 |
| control_gru | 1.000000 | -0.015312 | -0.017623 | -0.014200 | -0.017738 | -0.016218 | 0.001749 | -0.019001 | -0.013435 | 0/0/4 |
| control_gru_matched | 0.000000 | 0.003659 | 0.006414 | 0.001486 | 0.006161 | 0.004430 | 0.002323 | 0.000733 | 0.008127 | 4/0/0 |
| control_gru_matched | 0.500000 | -0.001498 | -0.000635 | -0.001258 | -0.003818 | -0.001802 | 0.001392 | -0.004018 | 0.000413 | 0/0/4 |
| control_gru_matched | 1.000000 | -0.014111 | -0.015488 | -0.013054 | -0.019706 | -0.015590 | 0.002919 | -0.020235 | -0.010944 | 0/0/4 |

At κ = 1, dense and the two monolithic controls have macro errors close to admissible; the monolithic results do not establish a distinctive advantage for the prescribed topology over every architecture. The misspecified arm retains cardiovascular → metabolic but removes cardiovascular → renal; its organ means help locate the resulting descriptive loss. These observations do not replace any registered comparator.

| Arm, κ = 1 | Parameters | Mean macro-NRMSE | Mean cardiovascular NRMSE | Mean renal NRMSE | Mean metabolic NRMSE |
| --- | --- | --- | --- | --- | --- |
| admissible | 271242 | 0.079999 | 0.048674 | 0.098169 | 0.093152 |
| none | 254086 | 0.096047 | 0.049847 | 0.117392 | 0.120902 |
| reversed | 271242 | 0.096741 | 0.050393 | 0.119730 | 0.120100 |
| random | 271242 | 0.091719 | 0.048343 | 0.113227 | 0.113588 |
| dense | 305554 | 0.081188 | 0.050869 | 0.099352 | 0.093343 |
| misspecified-1 | 271242 | 0.087632 | 0.049779 | 0.119257 | 0.093861 |
| control_gru | 61062 | 0.079829 | 0.049572 | 0.097102 | 0.092812 |
| control_gru_matched | 254472 | 0.080457 | 0.051078 | 0.096610 | 0.093684 |

The monolithic controls use gated recurrent units (GRUs) of hidden width 96 and 201, respectively. Width 201 approximately matches the no-edge graph parameter count, rather than the edge-bearing graph counts. They consume zero-imputed values and treatment controls but omit explicit masks; all graph edge comparisons share the same mask-aware input rules. Parameter counts are the saved `n_params`, not estimates.

The frozen random graphs also remain seed-specific and unchanged. In cardiovascular/renal/metabolic index order (0/1/2), the saved edges are:

| Seed | Saved random directed edges | Source |
| --- | --- | --- |
| 0 | [[1, 2], [2, 0]] | `kappa_1/random/seed0.json::edges` |
| 1 | [[1, 0], [1, 2]] | `kappa_1/random/seed1.json::edges` |
| 2 | [[0, 2], [2, 0]] | `kappa_1/random/seed2.json::edges` |
| 3 | [[0, 1], [2, 0]] | `kappa_1/random/seed3.json::edges` |

## Clinical observation lens

This lens measures source-history benefit for the fixed ridge oracle on the same held-out patients, not neural performance across observation rates. In the common-probability sweep, both targets use the displayed observation probability per five-minute row. The full registered curve is shown; there is no monotonicity assumption or interpolation. Each gain is `oracle_results.json::observation_lens.common_probability_sweep[i].per_organ[organ].rmse_relative_reduction`; the target-macro field is `target_macro_nrmse_fixed.rmse_relative_reduction` in that row.

| Common p per five-minute row | Renal G | Metabolic G | Target-macro G | Renal G ≥ 0.05 | Metabolic G ≥ 0.05 |
| --- | --- | --- | --- | --- | --- |
| 0.000000 | 0.224258 | 0.288757 | 0.256473 | PASS | PASS |
| 0.010000 | 0.202429 | 0.284590 | 0.242982 | PASS | PASS |
| 0.035000 | 0.212211 | 0.290387 | 0.251002 | PASS | PASS |
| 0.050000 | 0.214610 | 0.299705 | 0.257339 | PASS | PASS |
| 0.082748 | 0.209625 | 0.310489 | 0.261180 | PASS | PASS |
| 0.100000 | 0.212531 | 0.303080 | 0.258806 | PASS | PASS |
| 0.250000 | 0.265253 | 0.320315 | 0.292684 | PASS | PASS |
| 0.500000 | 0.271255 | 0.351923 | 0.312005 | PASS | PASS |
| 1.000000 | 0.257131 | 0.359325 | 0.309149 | PASS | PASS |

The largest tested probability meeting the 5% gain threshold is 1.000000 for renal and 1.000000 for metabolic, including fully observed target histories. Thus the oracle does not show a tested observation-rate cutoff where benefit disappears. The curve is not monotone; a transition beyond or between tested values is not inferred.

The measured clinical fractions below are pooled observed hourly rows divided by valid, non-padding hourly rows. They are saved rates from `oracle_results.json::clinical_rates.cohorts`, not newly recounted clinical data. Blood urea nitrogen is abbreviated BUN. The synthetic urine-output channel uses the union of creatinine/BUN availability as a declared proxy; the clinical archive has no urine-output feature.

| Saved clinical cohort | Creatinine hourly rate | BUN hourly rate | Either renal lab hourly rate | Lactate hourly rate |
| --- | --- | --- | --- | --- |
| A_train | 0.067026 | 0.082301 | 0.082748 | 0.034558 |
| A_all | 0.066920 | 0.082123 | 0.082534 | 0.034899 |
| B_all | 0.055534 | 0.055485 | 0.055541 | 0.018779 |

The primary neural experiment uses the A-train renal-union and lactate fractions as probabilities per five-minute row. This is more frequent observation per physical hour than in the clinical archive. The registered hourly-matched oracle sensitivity converts the rates using p_5min = 1 − (1 − p_hour)^(1/12), with independent bins. Primary unequal-rate gains are from `cells[1]`; sensitivity values are from `observation_lens.hourly_matched`.

| Oracle evaluation, κ = 1 | Renal p per five-minute row | Metabolic p per five-minute row | Renal G | Metabolic G | Target-macro G |
| --- | --- | --- | --- | --- | --- |
| Primary unequal rates | 0.082748 | 0.034558 | 0.209625 | 0.289632 | 0.250331 |
| Hourly-matched sensitivity | 0.007172 | 0.002926 | 0.206638 | 0.290314 | 0.247931 |

Clinical A-train creatinine, BUN, and renal-union hourly fractions and B’s renal-union fraction lie numerically in the sparse part of the tested common-p curve, but hourly and five-minute fractions are different units. The hourly-matched oracle still exceeds the gain threshold for both targets. Neither Bernoulli mask model reproduces clinical clustered or informative sampling, and there is no neural hourly-matched or observation-rate sweep in these fits.

## What the regime establishes

This constructed regime shows that the matched benchmark can detect useful prescribed cardiovascular-to-renal and cardiovascular-to-metabolic connections when densely observed recent cardiovascular innovations drive hidden perfusion reserve, the targets respond after transport delays, and noisy target histories provide incomplete information. Under the primary mask rates and dense synthetic supervision, the neural admissible arm passes every registered comparison at the strongest coupling and its advantage over each required comparator increases across the coupling grid; the no-coupling cell instead favors the comparison arms. The ridge oracle finds additional source information at every tested target-observation rate, including complete target observation and the separately converted clinical hourly rates. These are results from one generated population and four training/split seeds under the regime’s artificial stochastic drive, delayed target dynamics, fixed controls, dense cardiovascular observations, and independent sampling assumptions. They do not demonstrate a clinical edge benefit, identify true clinical causal structure, calibrate physiological coupling, establish neural benefit at all observation rates, prove superiority to the descriptive monolithic controls, or alter the original regime’s C3 null.

## Complete 96-fit inventory

All statuses are reconstructed as COMPLETE: `smoke=false`, `config.epochs=60`, a finite `curve` containing exactly epochs 1–60, finite metrics, and a final log record matching the result configuration and primary metric. Original fit process exit codes are not saved. For each row, the source link supplies `config.arm`, `config.kappa`, `config.seed`, `config.epochs`, `n_params`, `metrics.macro_nrmse_fixed`, and `metrics.organ_nrmse_fixed.{cardiovascular,renal,metabolic}`. JSON `runs` stores these field locators and result/log hashes per row.

| Arm | κ | Seed | Status | Epochs | Parameters | Macro-NRMSE | Cardiovascular | Renal | Metabolic | Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| admissible | 0.000000 | 0 | COMPLETE | 60 | 271242 | 0.068566 | 0.048104 | 0.079533 | 0.078059 | [R001](kappa_0/admissible/seed0.json) |
| admissible | 0.000000 | 1 | COMPLETE | 60 | 271242 | 0.071462 | 0.048618 | 0.083910 | 0.081858 | [R002](kappa_0/admissible/seed1.json) |
| admissible | 0.000000 | 2 | COMPLETE | 60 | 271242 | 0.071061 | 0.054201 | 0.079416 | 0.079566 | [R003](kappa_0/admissible/seed2.json) |
| admissible | 0.000000 | 3 | COMPLETE | 60 | 271242 | 0.064622 | 0.048399 | 0.071869 | 0.073600 | [R004](kappa_0/admissible/seed3.json) |
| none | 0.000000 | 0 | COMPLETE | 60 | 254086 | 0.064722 | 0.048268 | 0.074998 | 0.070899 | [R005](kappa_0/none/seed0.json) |
| none | 0.000000 | 1 | COMPLETE | 60 | 254086 | 0.064060 | 0.047818 | 0.073759 | 0.070603 | [R006](kappa_0/none/seed1.json) |
| none | 0.000000 | 2 | COMPLETE | 60 | 254086 | 0.066466 | 0.052187 | 0.073683 | 0.073528 | [R007](kappa_0/none/seed2.json) |
| none | 0.000000 | 3 | COMPLETE | 60 | 254086 | 0.061871 | 0.047442 | 0.068999 | 0.069173 | [R008](kappa_0/none/seed3.json) |
| reversed | 0.000000 | 0 | COMPLETE | 60 | 271242 | 0.065503 | 0.050827 | 0.074670 | 0.071012 | [R009](kappa_0/reversed/seed0.json) |
| reversed | 0.000000 | 1 | COMPLETE | 60 | 271242 | 0.063984 | 0.048212 | 0.073161 | 0.070577 | [R010](kappa_0/reversed/seed1.json) |
| reversed | 0.000000 | 2 | COMPLETE | 60 | 271242 | 0.067115 | 0.053767 | 0.074279 | 0.073299 | [R011](kappa_0/reversed/seed2.json) |
| reversed | 0.000000 | 3 | COMPLETE | 60 | 271242 | 0.062361 | 0.050023 | 0.068505 | 0.068555 | [R012](kappa_0/reversed/seed3.json) |
| random | 0.000000 | 0 | COMPLETE | 60 | 271242 | 0.066198 | 0.049705 | 0.076728 | 0.072162 | [R013](kappa_0/random/seed0.json) |
| random | 0.000000 | 1 | COMPLETE | 60 | 271242 | 0.065006 | 0.047165 | 0.073517 | 0.074335 | [R014](kappa_0/random/seed1.json) |
| random | 0.000000 | 2 | COMPLETE | 60 | 271242 | 0.067091 | 0.050159 | 0.072864 | 0.078251 | [R015](kappa_0/random/seed2.json) |
| random | 0.000000 | 3 | COMPLETE | 60 | 271242 | 0.063017 | 0.048779 | 0.070977 | 0.069296 | [R016](kappa_0/random/seed3.json) |
| dense | 0.000000 | 0 | COMPLETE | 60 | 305554 | 0.068681 | 0.051301 | 0.073938 | 0.080803 | [R017](kappa_0/dense/seed0.json) |
| dense | 0.000000 | 1 | COMPLETE | 60 | 305554 | 0.070661 | 0.048597 | 0.082979 | 0.080408 | [R018](kappa_0/dense/seed1.json) |
| dense | 0.000000 | 2 | COMPLETE | 60 | 305554 | 0.072162 | 0.052534 | 0.076828 | 0.087124 | [R019](kappa_0/dense/seed2.json) |
| dense | 0.000000 | 3 | COMPLETE | 60 | 305554 | 0.067072 | 0.049936 | 0.071506 | 0.079773 | [R020](kappa_0/dense/seed3.json) |
| misspecified-1 | 0.000000 | 0 | COMPLETE | 60 | 271242 | 0.069410 | 0.049136 | 0.076769 | 0.082324 | [R021](kappa_0/misspecified-1/seed0.json) |
| misspecified-1 | 0.000000 | 1 | COMPLETE | 60 | 271242 | 0.068363 | 0.048157 | 0.074039 | 0.082893 | [R022](kappa_0/misspecified-1/seed1.json) |
| misspecified-1 | 0.000000 | 2 | COMPLETE | 60 | 271242 | 0.069389 | 0.052592 | 0.074111 | 0.081463 | [R023](kappa_0/misspecified-1/seed2.json) |
| misspecified-1 | 0.000000 | 3 | COMPLETE | 60 | 271242 | 0.066230 | 0.048424 | 0.069673 | 0.080593 | [R024](kappa_0/misspecified-1/seed3.json) |
| control_gru | 0.000000 | 0 | COMPLETE | 60 | 61062 | 0.067762 | 0.048398 | 0.076817 | 0.078070 | [R025](kappa_0/control_gru/seed0.json) |
| control_gru | 0.000000 | 1 | COMPLETE | 60 | 61062 | 0.067280 | 0.046567 | 0.079874 | 0.075399 | [R026](kappa_0/control_gru/seed1.json) |
| control_gru | 0.000000 | 2 | COMPLETE | 60 | 61062 | 0.068544 | 0.051710 | 0.075800 | 0.078122 | [R027](kappa_0/control_gru/seed2.json) |
| control_gru | 0.000000 | 3 | COMPLETE | 60 | 61062 | 0.065324 | 0.047903 | 0.074287 | 0.073783 | [R028](kappa_0/control_gru/seed3.json) |
| control_gru_matched | 0.000000 | 0 | COMPLETE | 60 | 254472 | 0.068381 | 0.049006 | 0.077907 | 0.078230 | [R029](kappa_0/control_gru_matched/seed0.json) |
| control_gru_matched | 0.000000 | 1 | COMPLETE | 60 | 254472 | 0.070474 | 0.049989 | 0.079888 | 0.081545 | [R030](kappa_0/control_gru_matched/seed1.json) |
| control_gru_matched | 0.000000 | 2 | COMPLETE | 60 | 254472 | 0.067952 | 0.052724 | 0.073074 | 0.078059 | [R031](kappa_0/control_gru_matched/seed2.json) |
| control_gru_matched | 0.000000 | 3 | COMPLETE | 60 | 254472 | 0.068032 | 0.049291 | 0.077544 | 0.077262 | [R032](kappa_0/control_gru_matched/seed3.json) |
| admissible | 0.500000 | 0 | COMPLETE | 60 | 271242 | 0.070645 | 0.048589 | 0.082770 | 0.080574 | [R033](kappa_0.5/admissible/seed0.json) |
| admissible | 0.500000 | 1 | COMPLETE | 60 | 271242 | 0.071837 | 0.049259 | 0.083832 | 0.082419 | [R034](kappa_0.5/admissible/seed1.json) |
| admissible | 0.500000 | 2 | COMPLETE | 60 | 271242 | 0.073604 | 0.051314 | 0.084621 | 0.084878 | [R035](kappa_0.5/admissible/seed2.json) |
| admissible | 0.500000 | 3 | COMPLETE | 60 | 271242 | 0.070385 | 0.048382 | 0.084621 | 0.078152 | [R036](kappa_0.5/admissible/seed3.json) |
| none | 0.500000 | 0 | COMPLETE | 60 | 254086 | 0.073472 | 0.047356 | 0.086815 | 0.086244 | [R037](kappa_0.5/none/seed0.json) |
| none | 0.500000 | 1 | COMPLETE | 60 | 254086 | 0.074012 | 0.048630 | 0.085482 | 0.087923 | [R038](kappa_0.5/none/seed1.json) |
| none | 0.500000 | 2 | COMPLETE | 60 | 254086 | 0.075067 | 0.052205 | 0.085417 | 0.087579 | [R039](kappa_0.5/none/seed2.json) |
| none | 0.500000 | 3 | COMPLETE | 60 | 254086 | 0.073537 | 0.048851 | 0.086398 | 0.085362 | [R040](kappa_0.5/none/seed3.json) |
| reversed | 0.500000 | 0 | COMPLETE | 60 | 271242 | 0.074905 | 0.051649 | 0.086780 | 0.086286 | [R041](kappa_0.5/reversed/seed0.json) |
| reversed | 0.500000 | 1 | COMPLETE | 60 | 271242 | 0.073695 | 0.048604 | 0.086233 | 0.086248 | [R042](kappa_0.5/reversed/seed1.json) |
| reversed | 0.500000 | 2 | COMPLETE | 60 | 271242 | 0.076455 | 0.053373 | 0.088492 | 0.087501 | [R043](kappa_0.5/reversed/seed2.json) |
| reversed | 0.500000 | 3 | COMPLETE | 60 | 271242 | 0.073588 | 0.050251 | 0.085451 | 0.085060 | [R044](kappa_0.5/reversed/seed3.json) |
| random | 0.500000 | 0 | COMPLETE | 60 | 271242 | 0.074441 | 0.048773 | 0.085398 | 0.089151 | [R045](kappa_0.5/random/seed0.json) |
| random | 0.500000 | 1 | COMPLETE | 60 | 271242 | 0.072555 | 0.048687 | 0.085452 | 0.083526 | [R046](kappa_0.5/random/seed1.json) |
| random | 0.500000 | 2 | COMPLETE | 60 | 271242 | 0.073905 | 0.050853 | 0.085325 | 0.085537 | [R047](kappa_0.5/random/seed2.json) |
| random | 0.500000 | 3 | COMPLETE | 60 | 271242 | 0.072495 | 0.050365 | 0.079965 | 0.087157 | [R048](kappa_0.5/random/seed3.json) |
| dense | 0.500000 | 0 | COMPLETE | 60 | 305554 | 0.071618 | 0.050176 | 0.082869 | 0.081810 | [R049](kappa_0.5/dense/seed0.json) |
| dense | 0.500000 | 1 | COMPLETE | 60 | 305554 | 0.070145 | 0.049313 | 0.079679 | 0.081444 | [R050](kappa_0.5/dense/seed1.json) |
| dense | 0.500000 | 2 | COMPLETE | 60 | 305554 | 0.075611 | 0.054832 | 0.082527 | 0.089476 | [R051](kappa_0.5/dense/seed2.json) |
| dense | 0.500000 | 3 | COMPLETE | 60 | 305554 | 0.071537 | 0.049482 | 0.084168 | 0.080960 | [R052](kappa_0.5/dense/seed3.json) |
| misspecified-1 | 0.500000 | 0 | COMPLETE | 60 | 271242 | 0.070961 | 0.047666 | 0.085343 | 0.079874 | [R053](kappa_0.5/misspecified-1/seed0.json) |
| misspecified-1 | 0.500000 | 1 | COMPLETE | 60 | 271242 | 0.071545 | 0.046696 | 0.085486 | 0.082453 | [R054](kappa_0.5/misspecified-1/seed1.json) |
| misspecified-1 | 0.500000 | 2 | COMPLETE | 60 | 271242 | 0.075205 | 0.052755 | 0.089497 | 0.083364 | [R055](kappa_0.5/misspecified-1/seed2.json) |
| misspecified-1 | 0.500000 | 3 | COMPLETE | 60 | 271242 | 0.072379 | 0.049953 | 0.086262 | 0.080924 | [R056](kappa_0.5/misspecified-1/seed3.json) |
| control_gru | 0.500000 | 0 | COMPLETE | 60 | 61062 | 0.072877 | 0.051461 | 0.083195 | 0.083976 | [R057](kappa_0.5/control_gru/seed0.json) |
| control_gru | 0.500000 | 1 | COMPLETE | 60 | 61062 | 0.071031 | 0.047233 | 0.083850 | 0.082010 | [R058](kappa_0.5/control_gru/seed1.json) |
| control_gru | 0.500000 | 2 | COMPLETE | 60 | 61062 | 0.071770 | 0.050816 | 0.082421 | 0.082072 | [R059](kappa_0.5/control_gru/seed2.json) |
| control_gru | 0.500000 | 3 | COMPLETE | 60 | 61062 | 0.067359 | 0.047632 | 0.077027 | 0.077417 | [R060](kappa_0.5/control_gru/seed3.json) |
| control_gru_matched | 0.500000 | 0 | COMPLETE | 60 | 254472 | 0.071973 | 0.052590 | 0.081251 | 0.082079 | [R061](kappa_0.5/control_gru_matched/seed0.json) |
| control_gru_matched | 0.500000 | 1 | COMPLETE | 60 | 254472 | 0.073377 | 0.050360 | 0.085594 | 0.084178 | [R062](kappa_0.5/control_gru_matched/seed1.json) |
| control_gru_matched | 0.500000 | 2 | COMPLETE | 60 | 254472 | 0.073809 | 0.053377 | 0.083919 | 0.084132 | [R063](kappa_0.5/control_gru_matched/seed2.json) |
| control_gru_matched | 0.500000 | 3 | COMPLETE | 60 | 254472 | 0.069719 | 0.049721 | 0.081784 | 0.077651 | [R064](kappa_0.5/control_gru_matched/seed3.json) |
| admissible | 1.000000 | 0 | COMPLETE | 60 | 271242 | 0.078261 | 0.048019 | 0.095528 | 0.091237 | [R065](kappa_1/admissible/seed0.json) |
| admissible | 1.000000 | 1 | COMPLETE | 60 | 271242 | 0.080268 | 0.047209 | 0.098183 | 0.095413 | [R066](kappa_1/admissible/seed1.json) |
| admissible | 1.000000 | 2 | COMPLETE | 60 | 271242 | 0.081520 | 0.052438 | 0.096976 | 0.095146 | [R067](kappa_1/admissible/seed2.json) |
| admissible | 1.000000 | 3 | COMPLETE | 60 | 271242 | 0.079945 | 0.047032 | 0.101991 | 0.090812 | [R068](kappa_1/admissible/seed3.json) |
| none | 1.000000 | 0 | COMPLETE | 60 | 254086 | 0.095374 | 0.049073 | 0.116710 | 0.120339 | [R069](kappa_1/none/seed0.json) |
| none | 1.000000 | 1 | COMPLETE | 60 | 254086 | 0.096092 | 0.049617 | 0.114811 | 0.123847 | [R070](kappa_1/none/seed1.json) |
| none | 1.000000 | 2 | COMPLETE | 60 | 254086 | 0.096053 | 0.053195 | 0.116762 | 0.118203 | [R071](kappa_1/none/seed2.json) |
| none | 1.000000 | 3 | COMPLETE | 60 | 254086 | 0.096669 | 0.047504 | 0.121284 | 0.121218 | [R072](kappa_1/none/seed3.json) |
| reversed | 1.000000 | 0 | COMPLETE | 60 | 271242 | 0.096509 | 0.049593 | 0.119826 | 0.120108 | [R073](kappa_1/reversed/seed0.json) |
| reversed | 1.000000 | 1 | COMPLETE | 60 | 271242 | 0.095052 | 0.048409 | 0.119025 | 0.117722 | [R074](kappa_1/reversed/seed1.json) |
| reversed | 1.000000 | 2 | COMPLETE | 60 | 271242 | 0.097714 | 0.054616 | 0.119818 | 0.118708 | [R075](kappa_1/reversed/seed2.json) |
| reversed | 1.000000 | 3 | COMPLETE | 60 | 271242 | 0.097690 | 0.048957 | 0.120251 | 0.123863 | [R076](kappa_1/reversed/seed3.json) |
| random | 1.000000 | 0 | COMPLETE | 60 | 271242 | 0.095514 | 0.047386 | 0.118809 | 0.120347 | [R077](kappa_1/random/seed0.json) |
| random | 1.000000 | 1 | COMPLETE | 60 | 271242 | 0.095757 | 0.048818 | 0.117967 | 0.120485 | [R078](kappa_1/random/seed1.json) |
| random | 1.000000 | 2 | COMPLETE | 60 | 271242 | 0.086450 | 0.050019 | 0.119304 | 0.090027 | [R079](kappa_1/random/seed2.json) |
| random | 1.000000 | 3 | COMPLETE | 60 | 271242 | 0.089155 | 0.047149 | 0.096827 | 0.123491 | [R080](kappa_1/random/seed3.json) |
| dense | 1.000000 | 0 | COMPLETE | 60 | 305554 | 0.081206 | 0.051445 | 0.097951 | 0.094220 | [R081](kappa_1/dense/seed0.json) |
| dense | 1.000000 | 1 | COMPLETE | 60 | 305554 | 0.080957 | 0.048584 | 0.100665 | 0.093623 | [R082](kappa_1/dense/seed1.json) |
| dense | 1.000000 | 2 | COMPLETE | 60 | 305554 | 0.081642 | 0.053477 | 0.097821 | 0.093628 | [R083](kappa_1/dense/seed2.json) |
| dense | 1.000000 | 3 | COMPLETE | 60 | 305554 | 0.080947 | 0.049971 | 0.100970 | 0.091899 | [R084](kappa_1/dense/seed3.json) |
| misspecified-1 | 1.000000 | 0 | COMPLETE | 60 | 271242 | 0.086637 | 0.050347 | 0.116916 | 0.092649 | [R085](kappa_1/misspecified-1/seed0.json) |
| misspecified-1 | 1.000000 | 1 | COMPLETE | 60 | 271242 | 0.087466 | 0.048490 | 0.116516 | 0.097391 | [R086](kappa_1/misspecified-1/seed1.json) |
| misspecified-1 | 1.000000 | 2 | COMPLETE | 60 | 271242 | 0.089264 | 0.052357 | 0.122775 | 0.092659 | [R087](kappa_1/misspecified-1/seed2.json) |
| misspecified-1 | 1.000000 | 3 | COMPLETE | 60 | 271242 | 0.087162 | 0.047920 | 0.120821 | 0.092744 | [R088](kappa_1/misspecified-1/seed3.json) |
| control_gru | 1.000000 | 0 | COMPLETE | 60 | 61062 | 0.080062 | 0.050878 | 0.096329 | 0.092980 | [R089](kappa_1/control_gru/seed0.json) |
| control_gru | 1.000000 | 1 | COMPLETE | 60 | 61062 | 0.078469 | 0.048380 | 0.095523 | 0.091504 | [R090](kappa_1/control_gru/seed1.json) |
| control_gru | 1.000000 | 2 | COMPLETE | 60 | 61062 | 0.081853 | 0.050873 | 0.100127 | 0.094559 | [R091](kappa_1/control_gru/seed2.json) |
| control_gru | 1.000000 | 3 | COMPLETE | 60 | 61062 | 0.078931 | 0.048159 | 0.096429 | 0.092204 | [R092](kappa_1/control_gru/seed3.json) |
| control_gru_matched | 1.000000 | 0 | COMPLETE | 60 | 254472 | 0.081263 | 0.051762 | 0.096427 | 0.095600 | [R093](kappa_1/control_gru_matched/seed0.json) |
| control_gru_matched | 1.000000 | 1 | COMPLETE | 60 | 254472 | 0.080604 | 0.050691 | 0.096085 | 0.095035 | [R094](kappa_1/control_gru_matched/seed1.json) |
| control_gru_matched | 1.000000 | 2 | COMPLETE | 60 | 254472 | 0.082999 | 0.052752 | 0.100173 | 0.096072 | [R095](kappa_1/control_gru_matched/seed2.json) |
| control_gru_matched | 1.000000 | 3 | COMPLETE | 60 | 254472 | 0.076963 | 0.049106 | 0.093755 | 0.088028 | [R096](kappa_1/control_gru_matched/seed3.json) |

Engineering validation and all result-file SHA-256 values are in [DISTRIBUTION_NOTE.md](DISTRIBUTION_NOTE.md). project lead assessment and any required independent scientific review remain separate from this authored reading.
