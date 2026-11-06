# E3 matched randomized-dose comparator addendum — matched-comparator reading

The continuous-dose CRN adaptation trails the unadjusted 60-epoch Control-GRU on this identical onset-matched randomized-dose dataset in all six lambda/epoch arms for both exact and tolerance post-effect direction accuracy: each arm is lower in all four seed pairs, and every nominal 95% paired t interval lies below zero.

This analysis addendum resolves the missing same-dataset comparator in [E3_READING.md](E3_READING.md), its continuous-dose diagnostic section, and `e3_summary.json:diagnostic_requested_control_comparison`. Those files are preserved. The main-grid archive-provenance qualifications remain in force. This is an authored engineering/analysis handoff, not an independent scientific review or paper kit; scientific freezes and review eligibility are unchanged. The current final-kit/outside-review workflow applies, and paper prose metrics do not apply to this evidence report.

Full precision values, per-seed counts, source hashes, validation and paired identities are in [e3_summary_addendum.json](e3_summary_addendum.json); commands and UTC timing are in [DISTRIBUTION_NOTE.md](DISTRIBUTION_NOTE.md). Tables show six decimal places; calculations use unrounded inputs.

The four new controls use the identical 400-patient, dataset-seed-0 onset-matched randomized-dose archive as all 24 CRN runs: legacy policy (c, σ) = (0, 0), eventual dose drawn uniformly independently of severity. The archive SHA-256 is `f640b2a41740145e9b7127d03de2c0444db006148656ab0d393c9d0889635c0e`. Model/split seeds 0–3 reproduce the exact 280/120 train/test patient indices and factual-training normalization in each CRN arm. All 28 prediction archives were hash-checked and rescored; saved truth arrays, dose grids and scored indices match the common dataset exactly.

Control-GRU is the frozen 96-unit control-aware gated recurrent unit model, with 61,062 parameters and no balancing penalty. It uses the unchanged model builder, standard autoregressive factual trainer, alternative-plan predictor and direction scorer: 60 epochs, Adam learning rate 0.002, batch size 128 and gradient norm cap 1. Fits ran sequentially on CPU with two threads. Existing CRN runs used one thread. The continuous-dose counterfactual recurrent network (CRN) retains its distinct two-stage architecture and training schedule, including at λ=0. Equal total epochs therefore do not imply equal compute or training procedures.

Context is minutes 0–55 (12 samples); rollout is minutes 60–175 (24 samples). Both factual and alternative dosing begin at minute 72 (4,320 s). Scores use the 21 samples at minutes 75–175 and the four adjacent pairs among doses [0, 0.05, 0.10, 0.20, 0.40] micrograms/(kg minute). A cell is patient × adjacent dose pair × scored time × channel. Exact post-effect accuracy compares signs where true adjacent-dose change is nonzero: 60,480 cells per seed, with no exact true-zero cells (zero-effect accuracy is null, 0/0).

The tolerance variant maps absolute effects ≤ τ to zero in both prediction and truth, then scores cells with nonzero thresholded truth. In mean arterial pressure (MAP), heart rate (HR), cardiac output (CO), central venous pressure (CVP), urine output (UO) and lactate order, τ = [0.1 mmHg, 0.1 beats/min, 0.01 L/min, 0.05 mmHg, 0.01 mL/min, 0.01 mmol/L]. These are numerical sensitivity thresholds. Tolerance post-effect denominators for seeds 0–3 are [57,131, 56,796, 57,043, 56,427] for both models in every arm; their sum is 227,397. The corresponding tolerance-zero denominators are [3,349, 3,684, 3,437, 4,053].

Paired differences are CRN minus Control-GRU, matching model/split seed. Means are unweighted seed means. Each 95% paired t confidence interval (CI) is mean(d) ± 3.182446305284263 × sample_sd(d)/√4 (3 degrees of freedom); sign counts are positive/zero/negative unrounded differences. The intervals describe seed/split variability conditional on this one generated cohort, whose splits overlap. They do not treat individual direction cells as independent replicates and are nominal, without multiplicity correction.

| Control seed | Status / epochs | Exact post-effect: accuracy (correct/N) | Tolerance post-effect: accuracy (correct/N) | Run |
| --- | --- | --- | --- | --- |
| 0 | complete / 60 | 0.992063 (60000/60480) | 0.914092 (52223/57131) | [run](crn_diagnostic/control_gru/seed0/run.json) |
| 1 | complete / 60 | 0.972073 (58791/60480) | 0.860994 (48901/56796) | [run](crn_diagnostic/control_gru/seed1/run.json) |
| 2 | complete / 60 | 0.973644 (58886/60480) | 0.891345 (50845/57043) | [run](crn_diagnostic/control_gru/seed2/run.json) |
| 3 | complete / 60 | 0.985136 (59581/60480) | 0.890407 (50243/56427) | [run](crn_diagnostic/control_gru/seed3/run.json) |

Control-GRU exact mean ± sample SD is **0.980729 ± 0.009539**; tolerance post-effect mean ± sample SD is **0.889210 ± 0.021766**. Seed means are the reported estimands; the separately pooled tolerance accuracy is 0.889247 (202212/227397).

| CRN λ | CRN / control epochs | CRN exact mean | Exact Δ [95% paired t CI] | Sign +/0/− | CRN tolerance post-effect mean | Tolerance Δ [95% paired t CI] | Sign +/0/− |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 60 / 60 | 0.817675 | -0.163054 [-0.223327, -0.102780] | 0/0/4 | 0.752767 | -0.136442 [-0.253409, -0.019476] | 0/0/4 |
| 0 | 120 / 60 | 0.868605 | -0.112124 [-0.146562, -0.077685] | 0/0/4 | 0.814621 | -0.074589 [-0.140166, -0.009011] | 0/0/4 |
| 0.25 | 60 / 60 | 0.821164 | -0.159565 [-0.227671, -0.091459] | 0/0/4 | 0.780162 | -0.109048 [-0.207336, -0.010760] | 0/0/4 |
| 0.25 | 120 / 60 | 0.827360 | -0.153369 [-0.205070, -0.101668] | 0/0/4 | 0.778213 | -0.110996 [-0.196411, -0.025582] | 0/0/4 |
| 1 | 60 / 60 | 0.786950 | -0.193779 [-0.254491, -0.133067] | 0/0/4 | 0.724623 | -0.164586 [-0.279364, -0.049809] | 0/0/4 |
| 1 | 120 / 60 | 0.738984 | -0.241745 [-0.313446, -0.170044] | 0/0/4 | 0.660640 | -0.228570 [-0.338264, -0.118875] | 0/0/4 |

All rows use four paired seeds. Exact N = 60,480 per seed in both models (241,920 summed); tolerance post-effect N(seed0–3) = [57,131, 56,796, 57,043, 56,427] in both models (227,397 summed). The 60/60 rows match total epochs; every 120/60 row gives CRN twice the epoch budget and is not an equal-budget comparison. No 120-epoch Control-GRU was authorized or trained.

The best CRN mean occurs at λ=0 with 120 total epochs: exact accuracy 0.868605 versus Control-GRU 0.980729, a paired mean deficit of 0.112124; tolerance post-effect accuracy 0.814621 versus 0.889210, a deficit of 0.074589. Even this longer-budget CRN arm trails the 60-epoch control in every seed. The matched 60-epoch arms also all trail. There is no observed beat or tie among these arms, but the result is limited to this continuous-dose adaptation, cohort, seeds and scoring window. Architecture, loss and training differences prevent attribution of the deficit solely to adversarial balancing. Randomized dose assignment and matched onset do not establish all state–dose coverage or causal-identification assumptions.

The older Control-GRU (c, σ)=(0, 0) reference remains historical: its all-cell mean ± SD is 0.939656 ± 0.010178, with 69,120 cells per seed and alternative dosing starting at minute 60. Those values are quoted from the frozen counterfactual reading summary. They use a different intervention and scoring window, so they are not substituted for this comparator or subtracted from the new accuracies. The previous dependence-only point-0 contrasts also remain cross-policy context; the new same-archive contrasts above resolve the diagnostic gap directly. Main E3 support/dependence results, historical comparisons and scientific freezes are preserved.

Generated at 2026-11-05T14:42:33.363988+00:00 (UTC).
