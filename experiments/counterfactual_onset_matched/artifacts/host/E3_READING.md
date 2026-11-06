# E3 onset-matched counterfactual reading — counterfactual reading

Authored by the assigned research tooling research engineer from existing evidence. This is an analysis handoff, not an independent scientific review or a paper kit. The current final-kit/outside-review workflow supersedes old editorial gates; prose metrics do not apply to this evidence report. Scientific freezes, claims C4/C5 and review eligibility remain unchanged.

The package contains the complete **160 main rows and 24 continuous-dose CRN diagnostic rows**. Two material qualifications remain: the supplied diagnostic has no unadjusted Control-GRU fit on its identical randomized-dose dataset, and four main run records have historical dataset archive hashes that differ from the current manifests. The requested same-dataset diagnostic contrast is therefore unavailable; the main paired calculations below retain the archive-provenance qualification. Neither limitation is converted into a scientific PASS.

All numeric results are in [e3_summary.json](e3_summary.json). Floating results use six decimal places, integer counts are exact, and calculations use unrounded inputs. Each row links its source `run.json`; JSON `methods.row_source_fields` maps displayed fields to original fields, aggregate `source_run_ids` identify all contributing records, and paired records identify ordered A and B sources. [DISTRIBUTION_NOTE.md](DISTRIBUTION_NOTE.md) records commands, exits, hashes and UTC times.

## Operational questions and limits

The support-only family asks how direction recovery changes when the empirical 5th–95th percentile factual-dose interval within each severity tercile widens while global severity–dose Spearman rank correlation is held near 0.300000. The dependence-only family asks how recovery changes as that global rank correlation increases from target 0.000000 to 0.300000 while each tercile retains its entire factual-dose multiset and therefore its central support interval. These names describe measured assignment controls; finer conditional dependence and other assignment properties need not be isolated. The repaired CRN-lite now tests an adversarial penalty against a varying eventual factual-dose target, rather than a constant untreated-context target: all its train/test/all target distributions vary. This makes the intended conditional-mean balancing probe operational, but target variation does not demonstrate successful balancing, full distributional independence or causal identification. The dependence range is modest: identical tercile dose multisets cap attainable global rank dependence at approximately one third, so severe or deterministic global severity-driven assignment, other confounding structures, earlier-start interventions and broader state–dose coverage remain outside these runs. The calibrated near-zero rank point is not independent randomized treatment; the separate legacy-policy diagnostic randomizes eventual dose independently of severity and matches onset, without establishing all identification or estimator assumptions.

## Design, scoring and uncertainty

Every run uses dataset seed 0 and one of model/split seeds 0–3, with 400 patients split into 280 training and 120 test patients. Context contains 12 samples; rollout contains 24. Factual and alternative dosing begin at 4320 seconds (minute 72), and only the 21 samples at minutes 75–175 are scored. Alternative doses are [0.000000, 0.050000, 0.100000, 0.200000, 0.400000] micrograms/(kg minute). A direction cell is patient × adjacent-dose pair × scored time × channel: 60480 cells per full-grid run. The main fits have 60 epochs and CRN-lite λ=0.500000. Sources: `DESIGN_E3.md`, each row's `config` and `history_checks`, and `design_numbers` in the JSON.

Exact post-effect accuracy compares signs only where the stored true adjacent-dose effect is nonzero. Every supplied run has denominator 60480 there. Exact zero-effect accuracy is **null (0/0)** in every full-grid run; absence of zeros is not perfect zero-response performance. The sensitivity score maps magnitudes at or below τ to zero in both truth and prediction. In MAP, HR, CO, CVP, UO, lactate order, τ is [0.100000, 0.100000, 0.010000, 0.050000, 0.010000, 0.010000] in [mmHg, beats/min, L/min, mmHg, mL/min, mmol/L]. These are numerical sensitivity thresholds, not clinical effect thresholds. Full-grid tolerance post-effect denominators by seed are [57131,56796,57043,56427]; corresponding zero-effect denominators are [3349,3684,3437,4053]. The tolerance all-cell denominator remains 60480 per seed.

Means and sample standard deviations use four model/split seeds. Paired differences use the same seed and patient split, and, except for explicitly cross-policy comparisons, the same recorded assignment design. A 95% paired t interval is mean(d) ± t(0.975, df=3) × sample_sd(d)/sqrt(4), with t=3.182446. Sign counts are positive/zero/negative unrounded seed differences. These describe seed/split variability conditional on one generated cohort, without patient-sampling inference or multiplicity correction. The many direction cells are not independent replicates. Paired intervals are not clipped to the accuracy range.

Physical-unit root mean squared error (RMSE) uses 12600 patient × dose × scored-time values per channel in each run. Channels are never averaged across unlike physical units, and no new normalized RMSE denominator is compared to the old grid. Averages of tolerance accuracies are seed means; their exact per-seed counts and the separately calculated pooled accuracy are in the JSON.

## Policy coordinates for the fitted cohort

These are dataset-seed-0 measurements, not averages over the four policy-verification dataset seeds. The full 400-patient policy statistics determine the fitted policies; the 50-patient smoke statistics do not enter efficacy estimates. A supported dose lies in its patient's tercile central interval. A supported adjacent pair requires both doses in that interval.

| Family | Point | Width multiplier | Observed Spearman | Observed Pearson | Tercile 0/1/2 q05–q95 | Supported grid points | Restricted direction N/seed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| support_only | 0 | 0.100000 | 0.300004 | 0.305397 | [0.227500,0.272500]; [0.227500,0.272500]; [0.227500,0.272500] | 0/15 | 0 |
| support_only | 1 | 0.250000 | 0.300004 | 0.305397 | [0.193750,0.306250]; [0.193750,0.306250]; [0.193750,0.306250] | 3/15 | 0 |
| support_only | 2 | 0.500000 | 0.300004 | 0.305397 | [0.137500,0.362500]; [0.137500,0.362500]; [0.137500,0.362500] | 3/15 | 0 |
| support_only | 3 | 0.750000 | 0.300004 | 0.305397 | [0.081250,0.418750]; [0.081250,0.418750]; [0.081250,0.418750] | 9/15 | 30240 |
| support_only | 4 | 1.000000 | 0.300004 | 0.305397 | [0.025000,0.475000]; [0.025000,0.475000]; [0.025000,0.475000] | 12/15 | 45360 |
| dependence_only | 0 | 1.000000 | 0.000029 | -0.001189 | [0.025000,0.475000]; [0.025000,0.475000]; [0.025000,0.475000] | 12/15 | 45360 |
| dependence_only | 1 | 1.000000 | 0.075008 | 0.075406 | [0.025000,0.475000]; [0.025000,0.475000]; [0.025000,0.475000] | 12/15 | 45360 |
| dependence_only | 2 | 1.000000 | 0.149994 | 0.151788 | [0.025000,0.475000]; [0.025000,0.475000]; [0.025000,0.475000] | 12/15 | 45360 |
| dependence_only | 3 | 1.000000 | 0.225017 | 0.228211 | [0.025000,0.475000]; [0.025000,0.475000]; [0.025000,0.475000] | 12/15 | 45360 |
| dependence_only | 4 | 1.000000 | 0.300004 | 0.305397 | [0.025000,0.475000]; [0.025000,0.475000]; [0.025000,0.475000] | 12/15 | 45360 |

Support-only points 1 and 2 each cover one alternative dose per tercile but no adjacent pair, so their support-restricted direction accuracy is null (0/0), as at point 0. At point 3 two adjacent pairs are eligible; at point 4 three are eligible. The dependence family always includes doses [0.050000,0.100000,0.200000,0.400000] in the central interval, while zero remains outside it. Sources: `policy_points`, original `policy_statistics.json controlled_cells[*].policy.statistics`, and per-run `support`.

## One-dimensional reading: support at fixed dependence

At observed Spearman 0.300004 throughout, increasing the width multiplier from 0.100000 to 1.000000 increases mean post-effect direction recovery in every model. The largest change occurs while moving from the narrowest support toward the wider middle/high-support points. Control-GRU has a small mean decrease from point 3 to point 4; the other three mean sequences increase at each step. All models have positive endpoint changes in all four seeds, although their intermediate spread differs. Thus the measured narrow-support failures persist after onset matching, and much better recovery occurs with broader support at the same measured global dependence. This is an empirical result for these policies and models, not a general identification threshold.

| Point | Control-GRU post-effect | CRN-lite post-effect | PhysioGraph-GRU post-effect | PhysioGraph (SSM) post-effect |
| --- | --- | --- | --- | --- |
| 0 | 0.346982 ± 0.075269 (N=60480/seed) | 0.342349 ± 0.055259 (N=60480/seed) | 0.310334 ± 0.101946 (N=60480/seed) | 0.355018 ± 0.152422 (N=60480/seed) |
| 1 | 0.386314 ± 0.095164 (N=60480/seed) | 0.389654 ± 0.093479 (N=60480/seed) | 0.341481 ± 0.095457 (N=60480/seed) | 0.407614 ± 0.151705 (N=60480/seed) |
| 2 | 0.656374 ± 0.198109 (N=60480/seed) | 0.709867 ± 0.230516 (N=60480/seed) | 0.742125 ± 0.088819 (N=60480/seed) | 0.587591 ± 0.038409 (N=60480/seed) |
| 3 | 0.910644 ± 0.066532 (N=60480/seed) | 0.901844 ± 0.069563 (N=60480/seed) | 0.882519 ± 0.045243 (N=60480/seed) | 0.840394 ± 0.026011 (N=60480/seed) |
| 4 | 0.908548 ± 0.062189 (N=60480/seed) | 0.909317 ± 0.069149 (N=60480/seed) | 0.896681 ± 0.040697 (N=60480/seed) | 0.890480 ± 0.048738 (N=60480/seed) |

Endpoint contrast, point 4 minus point 0; both operands use exact post-effect denominators shown below:

| Model | Mean difference [95% paired t CI] | Sign +/0/− |
| --- | --- | --- |
| Control-GRU | 0.561566 [0.500367, 0.622765] (A:N=60480/seed; B:N=60480/seed) | 4/0/0 |
| CRN-lite | 0.566968 [0.500037, 0.633900] (A:N=60480/seed; B:N=60480/seed) | 4/0/0 |
| PhysioGraph-GRU | 0.586347 [0.451576, 0.721117] (A:N=60480/seed; B:N=60480/seed) | 4/0/0 |
| PhysioGraph (SSM) | 0.535462 [0.355023, 0.715901] (A:N=60480/seed; B:N=60480/seed) | 4/0/0 |

## One-dimensional reading: dependence at fixed support

With each tercile dose multiset fixed and central interval [0.025000,0.475000], the near-zero-rank point gives high post-effect recovery for every model. Mean recovery falls as target dependence increases to 0.300000. Control-GRU, CRN-lite and PhysioGraph-GRU decline at every step; PhysioGraph (SSM) has a local increase between points 1 and 2 and a lower endpoint overall. The endpoint paired intervals all include zero with only four seeds, so the mean trend is a descriptive finding with substantial seed uncertainty. There is no wholesale direction collapse within the measured dependence range, even at the shared anchor; the data do not test the severe dependence of the old deterministic endpoint.

| Point | Control-GRU post-effect | CRN-lite post-effect | PhysioGraph-GRU post-effect | PhysioGraph (SSM) post-effect |
| --- | --- | --- | --- | --- |
| 0 | 0.991249 ± 0.009247 (N=60480/seed) | 0.990985 ± 0.007970 (N=60480/seed) | 0.964083 ± 0.006647 (N=60480/seed) | 0.963736 ± 0.014363 (N=60480/seed) |
| 1 | 0.986305 ± 0.016366 (N=60480/seed) | 0.985181 ± 0.015881 (N=60480/seed) | 0.962847 ± 0.003739 (N=60480/seed) | 0.952360 ± 0.018992 (N=60480/seed) |
| 2 | 0.980072 ± 0.023591 (N=60480/seed) | 0.978051 ± 0.024414 (N=60480/seed) | 0.955642 ± 0.013018 (N=60480/seed) | 0.962798 ± 0.014565 (N=60480/seed) |
| 3 | 0.965989 ± 0.033396 (N=60480/seed) | 0.964170 ± 0.035874 (N=60480/seed) | 0.946999 ± 0.027704 (N=60480/seed) | 0.933470 ± 0.022937 (N=60480/seed) |
| 4 | 0.908548 ± 0.062189 (N=60480/seed) | 0.909317 ± 0.069149 (N=60480/seed) | 0.896681 ± 0.040697 (N=60480/seed) | 0.890480 ± 0.048738 (N=60480/seed) |

Endpoint contrast, point 4 minus point 0; both operands use exact post-effect denominators shown below:

| Model | Mean difference [95% paired t CI] | Sign +/0/− |
| --- | --- | --- |
| Control-GRU | -0.082701 [-0.178898, 0.013496] (A:N=60480/seed; B:N=60480/seed) | 1/0/3 |
| CRN-lite | -0.081667 [-0.187281, 0.023946] (A:N=60480/seed; B:N=60480/seed) | 1/0/3 |
| PhysioGraph-GRU | -0.067402 [-0.135178, 0.000373] (A:N=60480/seed; B:N=60480/seed) | 0/0/4 |
| PhysioGraph (SSM) | -0.073256 [-0.169711, 0.023199] (A:N=60480/seed; B:N=60480/seed) | 0/0/4 |

The support point-4 and dependence point-4 anchor yields exactly identical scores, RMSEs and target distributions for all sixteen model/seed pairs. It is a shared assignment anchor, not independent confirmation. Provenance: `main_aggregates`, `family_trends` and `shared_anchor_checks`.

## Repaired CRN-lite and model contrasts

The CRN-lite target is nonconstant in all 40 fits and all 120 all/train/test distributions. The smallest unique counts are 265 (all), 208 (train) and 102 (test). The smallest target standard deviations are 0.014542, 0.014050 and 0.014113 respectively. The head label is the assigned eventual dose, used only for the adversarial training loss; it is removed at inference. This repairs the constant-label defect described by historical C5. It does not make a continuous regression penalty a test of complete treatment–representation independence.

CRN-lite has no consistent improvement over Control-GRU across these points: every exact post-effect paired interval includes zero. Its largest positive mean difference occurs at support point 2, where all four differences are positive but the four-seed interval remains wide. This measured difference also means the old claim of near-equality within a fixed small band cannot simply be carried over to the repaired model. PhysioGraph (SSM) is below Control-GRU in every dependence-family mean; only the point-0 interval excludes zero at the nominal level, and this is not a multiplicity-adjusted superiority claim. PhysioGraph-GRU is reported separately so the node backbones are not conflated.

| Family | Point | A − Control-GRU | Exact post-effect Δ [95% CI] | Sign +/0/− | Tolerance post-effect Δ [95% CI] | Sign +/0/− |
| --- | --- | --- | --- | --- | --- | --- |
| support_only | 0 | CRN-lite | -0.004634 [-0.036556, 0.027289] (A:N=60480/seed; B:N=60480/seed) | 1/0/3 | -0.003412 [-0.038079, 0.031254] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 3/0/1 |
| support_only | 0 | PhysioGraph-GRU | -0.036648 [-0.185733, 0.112436] (A:N=60480/seed; B:N=60480/seed) | 1/0/3 | -0.061514 [-0.088698, -0.034330] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 0/0/4 |
| support_only | 0 | PhysioGraph (SSM) | 0.008036 [-0.223126, 0.239198] (A:N=60480/seed; B:N=60480/seed) | 2/0/2 | 0.062299 [-0.145992, 0.270591] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 3/0/1 |
| support_only | 1 | CRN-lite | 0.003340 [-0.006137, 0.012817] (A:N=60480/seed; B:N=60480/seed) | 2/0/2 | -0.004763 [-0.044312, 0.034787] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 3/0/1 |
| support_only | 1 | PhysioGraph-GRU | -0.044833 [-0.224152, 0.134486] (A:N=60480/seed; B:N=60480/seed) | 1/0/3 | -0.098104 [-0.137073, -0.059135] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 0/0/4 |
| support_only | 1 | PhysioGraph (SSM) | 0.021300 [-0.191311, 0.233912] (A:N=60480/seed; B:N=60480/seed) | 1/0/3 | 0.072205 [-0.136493, 0.280902] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 3/0/1 |
| support_only | 2 | CRN-lite | 0.053493 [-0.052079, 0.159065] (A:N=60480/seed; B:N=60480/seed) | 4/0/0 | 0.009300 [-0.004409, 0.023009] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 4/0/0 |
| support_only | 2 | PhysioGraph-GRU | 0.085751 [-0.103481, 0.274984] (A:N=60480/seed; B:N=60480/seed) | 4/0/0 | -0.086241 [-0.168776, -0.003706] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 0/0/4 |
| support_only | 2 | PhysioGraph (SSM) | -0.068783 [-0.325664, 0.188098] (A:N=60480/seed; B:N=60480/seed) | 1/0/3 | 0.074274 [0.013222, 0.135327] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 4/0/0 |
| support_only | 3 | CRN-lite | -0.008800 [-0.027641, 0.010040] (A:N=60480/seed; B:N=60480/seed) | 1/0/3 | 0.007296 [-0.043858, 0.058449] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 3/0/1 |
| support_only | 3 | PhysioGraph-GRU | -0.028125 [-0.067466, 0.011216] (A:N=60480/seed; B:N=60480/seed) | 0/0/4 | 0.033744 [-0.015475, 0.082963] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 4/0/0 |
| support_only | 3 | PhysioGraph (SSM) | -0.070250 [-0.158824, 0.018323] (A:N=60480/seed; B:N=60480/seed) | 0/1/3 | -0.054094 [-0.226005, 0.117818] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 1/0/3 |
| support_only | 4 | CRN-lite | 0.000769 [-0.032322, 0.033859] (A:N=60480/seed; B:N=60480/seed) | 2/0/2 | 0.006573 [-0.008848, 0.021994] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 3/0/1 |
| support_only | 4 | PhysioGraph-GRU | -0.011868 [-0.056172, 0.032437] (A:N=60480/seed; B:N=60480/seed) | 1/0/3 | 0.012033 [-0.048122, 0.072187] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 3/0/1 |
| support_only | 4 | PhysioGraph (SSM) | -0.018068 [-0.061685, 0.025549] (A:N=60480/seed; B:N=60480/seed) | 1/0/3 | -0.026802 [-0.105175, 0.051571] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 1/0/3 |
| dependence_only | 0 | CRN-lite | -0.000265 [-0.009184, 0.008655] (A:N=60480/seed; B:N=60480/seed) | 3/0/1 | 0.003897 [-0.020607, 0.028402] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 1/0/3 |
| dependence_only | 0 | PhysioGraph-GRU | -0.027166 [-0.031692, -0.022640] (A:N=60480/seed; B:N=60480/seed) | 0/0/4 | -0.022198 [-0.062708, 0.018313] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 1/0/3 |
| dependence_only | 0 | PhysioGraph (SSM) | -0.027513 [-0.053839, -0.001187] (A:N=60480/seed; B:N=60480/seed) | 0/0/4 | -0.025033 [-0.070269, 0.020204] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 1/0/3 |
| dependence_only | 1 | CRN-lite | -0.001124 [-0.010458, 0.008209] (A:N=60480/seed; B:N=60480/seed) | 3/0/1 | 0.004876 [-0.022212, 0.031964] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 1/0/3 |
| dependence_only | 1 | PhysioGraph-GRU | -0.023458 [-0.050149, 0.003232] (A:N=60480/seed; B:N=60480/seed) | 0/0/4 | -0.019652 [-0.067993, 0.028689] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 1/0/3 |
| dependence_only | 1 | PhysioGraph (SSM) | -0.033945 [-0.086812, 0.018921] (A:N=60480/seed; B:N=60480/seed) | 1/0/3 | -0.038092 [-0.115952, 0.039769] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 1/0/3 |
| dependence_only | 2 | CRN-lite | -0.002021 [-0.014947, 0.010904] (A:N=60480/seed; B:N=60480/seed) | 3/0/1 | 0.004598 [-0.023176, 0.032372] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 2/0/2 |
| dependence_only | 2 | PhysioGraph-GRU | -0.024430 [-0.058630, 0.009771] (A:N=60480/seed; B:N=60480/seed) | 0/0/4 | -0.007478 [-0.033358, 0.018401] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 1/0/3 |
| dependence_only | 2 | PhysioGraph (SSM) | -0.017274 [-0.052912, 0.018364] (A:N=60480/seed; B:N=60480/seed) | 1/0/3 | -0.021126 [-0.083454, 0.041202] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 1/0/3 |
| dependence_only | 3 | CRN-lite | -0.001819 [-0.023350, 0.019712] (A:N=60480/seed; B:N=60480/seed) | 3/0/1 | 0.003887 [-0.021689, 0.029463] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 2/0/2 |
| dependence_only | 3 | PhysioGraph-GRU | -0.018990 [-0.062231, 0.024251] (A:N=60480/seed; B:N=60480/seed) | 1/0/3 | 0.006157 [-0.023914, 0.036227] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 3/0/1 |
| dependence_only | 3 | PhysioGraph (SSM) | -0.032519 [-0.087343, 0.022305] (A:N=60480/seed; B:N=60480/seed) | 1/0/3 | -0.041436 [-0.122135, 0.039262] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 1/0/3 |
| dependence_only | 4 | CRN-lite | 0.000769 [-0.032322, 0.033859] (A:N=60480/seed; B:N=60480/seed) | 2/0/2 | 0.006573 [-0.008848, 0.021994] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 3/0/1 |
| dependence_only | 4 | PhysioGraph-GRU | -0.011868 [-0.056172, 0.032437] (A:N=60480/seed; B:N=60480/seed) | 1/0/3 | 0.012033 [-0.048122, 0.072187] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 3/0/1 |
| dependence_only | 4 | PhysioGraph (SSM) | -0.018068 [-0.061685, 0.025549] (A:N=60480/seed; B:N=60480/seed) | 1/0/3 | -0.026802 [-0.105175, 0.051571] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 1/0/3 |

All primary model contrasts, tolerance all/zero contrasts, support-restricted contrasts and channel RMSE contrasts are retained in `main_paired_differences`. Counts are signs of differences, not the number of correct direction cells.

## Continuous-dose CRN randomized-dose diagnostic

This diagnostic uses onset-matched legacy-policy (c,σ)=(0.000000,0.000000) data, with eventual dose randomized independently of severity. The observed finite-cohort Spearman is 0.031276 and Pearson is 0.031585. All λ values keep the same full continuous-dose CRN architecture; λ=0 does not become Control-GRU. The total epoch budgets are 60 or 120, with the original two-stage split. Sources: `diagnostic_rows[*].config`, `policy.statistics` and `diagnostic_aggregates`.

| λ | Total epochs | Exact post-effect mean ± sd | Exact zero-effect | Tolerance all mean ± sd | Tolerance post-effect mean ± sd | Tolerance zero-effect mean ± sd |
| --- | --- | --- | --- | --- | --- | --- |
| 0.000000 | 60 | 0.817675 ± 0.028593 (N=60480/seed) | null (0/0) | 0.733999 ± 0.048410 (N=60480/seed) | 0.752767 ± 0.055512 (N(seed0–3)=[57131,56796,57043,56427]) | 0.442929 ± 0.082903 (N(seed0–3)=[3349,3684,3437,4053]) |
| 0.000000 | 120 | 0.868605 ± 0.024099 (N=60480/seed) | null (0/0) | 0.791080 ± 0.030301 (N=60480/seed) | 0.814621 ± 0.038498 (N(seed0–3)=[57131,56796,57043,56427]) | 0.428323 ± 0.098590 (N(seed0–3)=[3349,3684,3437,4053]) |
| 0.250000 | 60 | 0.821164 ± 0.042694 (N=60480/seed) | null (0/0) | 0.748388 ± 0.048317 (N=60480/seed) | 0.780162 ± 0.053197 (N(seed0–3)=[57131,56796,57043,56427]) | 0.254162 ± 0.029039 (N(seed0–3)=[3349,3684,3437,4053]) |
| 0.250000 | 120 | 0.827360 ± 0.039336 (N=60480/seed) | null (0/0) | 0.750079 ± 0.048083 (N=60480/seed) | 0.778213 ± 0.057552 (N(seed0–3)=[57131,56796,57043,56427]) | 0.309951 ± 0.108145 (N(seed0–3)=[3349,3684,3437,4053]) |
| 1.000000 | 60 | 0.786950 ± 0.039393 (N=60480/seed) | null (0/0) | 0.698909 ± 0.054702 (N=60480/seed) | 0.724623 ± 0.063258 (N(seed0–3)=[57131,56796,57043,56427]) | 0.302815 ± 0.038268 (N(seed0–3)=[3349,3684,3437,4053]) |
| 1.000000 | 120 | 0.738984 ± 0.048911 (N=60480/seed) | null (0/0) | 0.643374 ± 0.058246 (N=60480/seed) | 0.660640 ± 0.065392 (N(seed0–3)=[57131,56796,57043,56427]) | 0.370811 ± 0.075942 (N(seed0–3)=[3349,3684,3437,4053]) |

The largest diagnostic mean is at λ=0.000000 with 120 total epochs. More epochs help λ=0.000000 on average, change λ=0.250000 less, and reduce λ=1.000000 performance on average. These are outcomes of this adaptation and budget, without a sole attribution to balancing, optimization or identification.

| λ | Epochs when fixed | Within-CRN contrast | Post-effect Δ [95% paired t CI] | Sign +/0/− |
| --- | --- | --- | --- | --- |
| 0.000000 | 60→120 | epochs120 - epochs60 | 0.050930 [-0.017302, 0.119162] (A:N=60480/seed; B:N=60480/seed) | 3/0/1 |
| 0.250000 | 60 | lambda - lambda0 | 0.003489 [-0.082227, 0.089204] (A:N=60480/seed; B:N=60480/seed) | 3/0/1 |
| 0.250000 | 120 | lambda - lambda0 | -0.041245 [-0.087156, 0.004666] (A:N=60480/seed; B:N=60480/seed) | 0/0/4 |
| 0.250000 | 60→120 | epochs120 - epochs60 | 0.006196 [-0.048504, 0.060896] (A:N=60480/seed; B:N=60480/seed) | 2/0/2 |
| 1.000000 | 60 | lambda - lambda0 | -0.030725 [-0.109201, 0.047751] (A:N=60480/seed; B:N=60480/seed) | 1/0/3 |
| 1.000000 | 120 | lambda - lambda0 | -0.129621 [-0.195691, -0.063552] (A:N=60480/seed; B:N=60480/seed) | 0/0/4 |
| 1.000000 | 60→120 | epochs120 - epochs60 | -0.047966 [-0.146047, 0.050115] (A:N=60480/seed; B:N=60480/seed) | 1/0/3 |

**The requested same-dataset comparison against unadjusted Control-GRU cannot be computed from the supplied records.** There are no Control-GRU runs on this onset-matched randomized legacy-dose dataset. Historical Control-GRU results use an earlier-start intervention, and dependence-only point 0 uses a calibrated assignment with a different realized dose allocation. Neither is a valid replacement for a same-assignment comparison. No training was authorized or performed. `diagnostic_requested_control_comparison.paired_difference` is null, with the needed existing evidence specified.

For transparent context only, the following differences match model/split seed against the existing dependence-only point-0 Control-GRU. They compare different factual policies, so the interval cannot isolate a model difference; the 120-epoch rows additionally compare unequal budgets against a 60-epoch GRU. This contextual calculation does not satisfy the missing same-dataset diagnostic comparison.

| CRN λ | CRN epochs | CRN − dependence-only p0 Control-GRU, post-effect Δ [95% CI] | Sign +/0/− |
| --- | --- | --- | --- |
| 0.000000 | 60 | -0.173574 [-0.221025, -0.126123] (A:N=60480/seed; B:N=60480/seed) | 0/0/4 |
| 0.000000 | 120 | -0.122644 [-0.171783, -0.073505] (A:N=60480/seed; B:N=60480/seed) | 0/0/4 |
| 0.250000 | 60 | -0.170085 [-0.241869, -0.098301] (A:N=60480/seed; B:N=60480/seed) | 0/0/4 |
| 0.250000 | 120 | -0.163889 [-0.228978, -0.098799] (A:N=60480/seed; B:N=60480/seed) | 0/0/4 |
| 1.000000 | 60 | -0.204299 [-0.280763, -0.127835] (A:N=60480/seed; B:N=60480/seed) | 0/0/4 |
| 1.000000 | 120 | -0.252265 [-0.327461, -0.177069] (A:N=60480/seed; B:N=60480/seed) | 0/0/4 |

## Comparison with the earlier c × σ grid

The earlier shared-history grid has 384 fits across 24 policy settings and four models, within an aggregate that also contains 48 older-protocol fits. Its direction accuracy uses 69120 cells per run across the entire rollout; 2400 true-zero cells include the pre-switch sample. Its alternative treatment starts at minute 60, before factual onset at minute 72. New E3 scores only the strictly post-onset window, with 60480/60480 true nonzero-effect cells in every run. Old all-cell accuracy and new post-effect accuracy have different interventions and denominators; subtracting them is not an onset-only effect estimate. No onset-matched version of the full old c × σ model grid is supplied.

Selected historical Control-GRU cells are shown for scale. These are old all-cell accuracies, not newly rescored post-effect results. The original summary provides population-average direction counts as a separate statistic; E3 adjacent-cell accuracy is not substituted for that population-sign statistic.

| Old c | Old σ | Old all-cell mean ± sd (N/seed) | Observed Spearman | Observed Pearson | Supported dose cells | Population direction count mean / 3 |
| --- | --- | --- | --- | --- | --- | --- |
| 0.000000 | 0.000000 | 0.939656 ± 0.010178 (N=69120/seed) | 0.031276 | 0.031585 | 12/15 | 3.000000 / 3 |
| 0.100000 | 0.000000 | 0.925666 ± 0.016582 (N=69120/seed) | 0.106891 | 0.106366 | 11/15 | 3.000000 / 3 |
| 0.250000 | 0.000000 | 0.819976 ± 0.038287 (N=69120/seed) | 0.245076 | 0.249564 | 8/15 | 2.000000 / 3 |
| 0.500000 | 0.000000 | 0.320048 ± 0.001916 (N=69120/seed) | 0.560891 | 0.578898 | 4/15 | 0.000000 / 3 |
| 0.750000 | 0.000000 | 0.304344 ± 0.011318 (N=69120/seed) | 0.904037 | 0.900159 | 3/15 | 0.000000 / 3 |
| 1.000000 | 0.000000 | 0.302398 ± 0.012735 (N=69120/seed) | 1.000000 | 1.000000 | 2/15 | 0.000000 / 3 |
| 1.000000 | 0.080000 | 0.318370 ± 0.002348 (N=69120/seed) | 0.812933 | 0.801806 | 6/15 | 0.000000 / 3 |
| 1.000000 | 0.150000 | 0.760156 ± 0.018161 (N=69120/seed) | 0.582289 | 0.577537 | 11/15 | 2.000000 / 3 |
| 1.000000 | 0.250000 | 0.830396 ± 0.048814 (N=69120/seed) | 0.383437 | 0.374184 | 15/15 | 2.250000 / 3 |

In the old policy, changing σ changes conditional dose support and severity–dose correlation together; σ=0 still retains the uniform random component whenever c<1. E3 supplies two controlled operational slices after matching onset. It shows a strong support-width association at fixed rank dependence, plus a smaller descriptive dependence association at fixed tercile dose distributions. It does not retest the old grid's high-dependence collapse or attribute all old failures to support loss. Repairing CRN-lite also changes the estimator, so old near-equality with GRU does not establish that balancing never matters.

The old `H5_READING.md` contains stronger interpretations about separation, an identifiable/positive control and sole estimator failure. The current C4/C5 ledger explicitly qualifies those statements; this report follows the ledger and `DESIGN_E3.md`, not those superseded interpretations. Supported isolated dose points can exist even when no adjacent pair is evaluable. No causal-identification claim is made beyond the design. All 96 historical model/policy summaries, their measured policy statistics and original source fields are retained in `legacy_comparison.cells`.

## Four-seed tolerance and restricted summaries

Each entry is mean ± sample sd with its four exact denominators. Empty exact zero-effect subsets remain null (0/0). Per-channel exact/tolerance summaries, counts and pooled values are also available in `main_aggregates`.

| Family | Point | Model | Tolerance all | Tolerance post-effect | Tolerance zero-effect | Restricted exact post-effect |
| --- | --- | --- | --- | --- | --- | --- |
| support_only | 0 | Control-GRU | 0.143419 ± 0.023481 (N=60480/seed) | 0.096749 ± 0.027683 (N(seed0–3)=[57131,56796,57043,56427]) | 0.874928 ± 0.059165 (N(seed0–3)=[3349,3684,3437,4053]) | null ± null (N=0/seed) |
| support_only | 0 | CRN-lite | 0.140332 ± 0.037483 (N=60480/seed) | 0.093337 ± 0.041949 (N(seed0–3)=[57131,56796,57043,56427]) | 0.878886 ± 0.068361 (N(seed0–3)=[3349,3684,3437,4053]) | null ± null (N=0/seed) |
| support_only | 0 | PhysioGraph-GRU | 0.091456 ± 0.024868 (N=60480/seed) | 0.035235 ± 0.023942 (N(seed0–3)=[57131,56796,57043,56427]) | 0.971715 ± 0.035955 (N(seed0–3)=[3349,3684,3437,4053]) | null ± null (N=0/seed) |
| support_only | 0 | PhysioGraph (SSM) | 0.198181 ± 0.101340 (N=60480/seed) | 0.159048 ± 0.112024 (N(seed0–3)=[57131,56796,57043,56427]) | 0.805216 ± 0.095151 (N(seed0–3)=[3349,3684,3437,4053]) | null ± null (N=0/seed) |
| support_only | 1 | Control-GRU | 0.186293 ± 0.019601 (N=60480/seed) | 0.144618 ± 0.025629 (N(seed0–3)=[57131,56796,57043,56427]) | 0.838661 ± 0.091395 (N(seed0–3)=[3349,3684,3437,4053]) | null ± null (N=0/seed) |
| support_only | 1 | CRN-lite | 0.181820 ± 0.027457 (N=60480/seed) | 0.139856 ± 0.033818 (N(seed0–3)=[57131,56796,57043,56427]) | 0.840608 ± 0.099820 (N(seed0–3)=[3349,3684,3437,4053]) | null ± null (N=0/seed) |
| support_only | 1 | PhysioGraph-GRU | 0.099855 ± 0.017515 (N=60480/seed) | 0.046514 ± 0.012833 (N(seed0–3)=[57131,56796,57043,56427]) | 0.934181 ± 0.076199 (N(seed0–3)=[3349,3684,3437,4053]) | null ± null (N=0/seed) |
| support_only | 1 | PhysioGraph (SSM) | 0.251525 ± 0.117469 (N=60480/seed) | 0.216823 ± 0.125255 (N(seed0–3)=[57131,56796,57043,56427]) | 0.785803 ± 0.107256 (N(seed0–3)=[3349,3684,3437,4053]) | null ± null (N=0/seed) |
| support_only | 2 | Control-GRU | 0.318605 ± 0.050939 (N=60480/seed) | 0.284823 ± 0.050944 (N(seed0–3)=[57131,56796,57043,56427]) | 0.850096 ± 0.061235 (N(seed0–3)=[3349,3684,3437,4053]) | null ± null (N=0/seed) |
| support_only | 2 | CRN-lite | 0.327286 ± 0.053165 (N=60480/seed) | 0.294123 ± 0.052046 (N(seed0–3)=[57131,56796,57043,56427]) | 0.848834 ± 0.076076 (N(seed0–3)=[3349,3684,3437,4053]) | null ± null (N=0/seed) |
| support_only | 2 | PhysioGraph-GRU | 0.242684 ± 0.090362 (N=60480/seed) | 0.198582 ± 0.089621 (N(seed0–3)=[57131,56796,57043,56427]) | 0.937033 ± 0.070798 (N(seed0–3)=[3349,3684,3437,4053]) | null ± null (N=0/seed) |
| support_only | 2 | PhysioGraph (SSM) | 0.385421 ± 0.065300 (N=60480/seed) | 0.359097 ± 0.061831 (N(seed0–3)=[57131,56796,57043,56427]) | 0.791339 ± 0.149568 (N(seed0–3)=[3349,3684,3437,4053]) | null ± null (N=0/seed) |
| support_only | 3 | Control-GRU | 0.661686 ± 0.056718 (N=60480/seed) | 0.653668 ± 0.060453 (N(seed0–3)=[57131,56796,57043,56427]) | 0.790409 ± 0.045452 (N(seed0–3)=[3349,3684,3437,4053]) | 0.909871 ± 0.066866 (N=30240/seed) |
| support_only | 3 | CRN-lite | 0.667981 ± 0.049632 (N=60480/seed) | 0.660963 ± 0.049739 (N(seed0–3)=[57131,56796,57043,56427]) | 0.777344 ± 0.056517 (N(seed0–3)=[3349,3684,3437,4053]) | 0.901637 ± 0.069678 (N=30240/seed) |
| support_only | 3 | PhysioGraph-GRU | 0.689753 ± 0.067246 (N=60480/seed) | 0.687411 ± 0.073358 (N(seed0–3)=[57131,56796,57043,56427]) | 0.735082 ± 0.096665 (N(seed0–3)=[3349,3684,3437,4053]) | 0.879580 ± 0.043555 (N=30240/seed) |
| support_only | 3 | PhysioGraph (SSM) | 0.608929 ± 0.063732 (N=60480/seed) | 0.599574 ± 0.072764 (N(seed0–3)=[57131,56796,57043,56427]) | 0.751784 ± 0.186728 (N(seed0–3)=[3349,3684,3437,4053]) | 0.841997 ± 0.027603 (N=30240/seed) |
| support_only | 4 | Control-GRU | 0.767613 ± 0.056818 (N=60480/seed) | 0.775208 ± 0.060279 (N(seed0–3)=[57131,56796,57043,56427]) | 0.649567 ± 0.061000 (N(seed0–3)=[3349,3684,3437,4053]) | 0.907474 ± 0.062946 (N=45360/seed) |
| support_only | 4 | CRN-lite | 0.772640 ± 0.053379 (N=60480/seed) | 0.781781 ± 0.054135 (N(seed0–3)=[57131,56796,57043,56427]) | 0.628150 ± 0.080188 (N(seed0–3)=[3349,3684,3437,4053]) | 0.908868 ± 0.069225 (N=45360/seed) |
| support_only | 4 | PhysioGraph-GRU | 0.778956 ± 0.030356 (N=60480/seed) | 0.787241 ± 0.033446 (N(seed0–3)=[57131,56796,57043,56427]) | 0.651075 ± 0.032576 (N(seed0–3)=[3349,3684,3437,4053]) | 0.894841 ± 0.042918 (N=45360/seed) |
| support_only | 4 | PhysioGraph (SSM) | 0.739641 ± 0.032221 (N=60480/seed) | 0.748406 ± 0.036977 (N(seed0–3)=[57131,56796,57043,56427]) | 0.605445 ± 0.150093 (N(seed0–3)=[3349,3684,3437,4053]) | 0.890757 ± 0.049789 (N=45360/seed) |
| dependence_only | 0 | Control-GRU | 0.888252 ± 0.010473 (N=60480/seed) | 0.916600 ± 0.011511 (N(seed0–3)=[57131,56796,57043,56427]) | 0.440096 ± 0.067458 (N(seed0–3)=[3349,3684,3437,4053]) | 0.991727 ± 0.009882 (N=45360/seed) |
| dependence_only | 0 | CRN-lite | 0.892101 ± 0.013000 (N=60480/seed) | 0.920498 ± 0.016898 (N(seed0–3)=[57131,56796,57043,56427]) | 0.444472 ± 0.073720 (N(seed0–3)=[3349,3684,3437,4053]) | 0.991336 ± 0.008472 (N=45360/seed) |
| dependence_only | 0 | PhysioGraph-GRU | 0.867816 ± 0.017149 (N=60480/seed) | 0.894403 ± 0.020143 (N(seed0–3)=[57131,56796,57043,56427]) | 0.446377 ± 0.122988 (N(seed0–3)=[3349,3684,3437,4053]) | 0.967554 ± 0.013111 (N=45360/seed) |
| dependence_only | 0 | PhysioGraph (SSM) | 0.863819 ± 0.030131 (N=60480/seed) | 0.891568 ± 0.033235 (N(seed0–3)=[57131,56796,57043,56427]) | 0.433657 ± 0.097595 (N(seed0–3)=[3349,3684,3437,4053]) | 0.966077 ± 0.014269 (N=45360/seed) |
| dependence_only | 1 | Control-GRU | 0.881510 ± 0.015721 (N=60480/seed) | 0.905983 ± 0.017035 (N(seed0–3)=[57131,56796,57043,56427]) | 0.494701 ± 0.044558 (N(seed0–3)=[3349,3684,3437,4053]) | 0.986232 ± 0.017010 (N=45360/seed) |
| dependence_only | 1 | CRN-lite | 0.885962 ± 0.019946 (N=60480/seed) | 0.910859 ± 0.022490 (N(seed0–3)=[57131,56796,57043,56427]) | 0.493173 ± 0.043752 (N(seed0–3)=[3349,3684,3437,4053]) | 0.985185 ± 0.016463 (N=45360/seed) |
| dependence_only | 1 | PhysioGraph-GRU | 0.864042 ± 0.017587 (N=60480/seed) | 0.886331 ± 0.018742 (N(seed0–3)=[57131,56796,57043,56427]) | 0.511194 ± 0.089181 (N(seed0–3)=[3349,3684,3437,4053]) | 0.966694 ± 0.009371 (N=45360/seed) |
| dependence_only | 1 | PhysioGraph (SSM) | 0.845387 ± 0.038140 (N=60480/seed) | 0.867892 ± 0.043715 (N(seed0–3)=[57131,56796,57043,56427]) | 0.500073 ± 0.114479 (N(seed0–3)=[3349,3684,3437,4053]) | 0.953175 ± 0.021028 (N=45360/seed) |
| dependence_only | 2 | Control-GRU | 0.868643 ± 0.023645 (N=60480/seed) | 0.888976 ± 0.025100 (N(seed0–3)=[57131,56796,57043,56427]) | 0.546902 ± 0.041249 (N(seed0–3)=[3349,3684,3437,4053]) | 0.979575 ± 0.024410 (N=45360/seed) |
| dependence_only | 2 | CRN-lite | 0.872168 ± 0.025635 (N=60480/seed) | 0.893574 ± 0.027157 (N(seed0–3)=[57131,56796,57043,56427]) | 0.533831 ± 0.030801 (N(seed0–3)=[3349,3684,3437,4053]) | 0.977508 ± 0.025267 (N=45360/seed) |
| dependence_only | 2 | PhysioGraph-GRU | 0.860231 ± 0.012602 (N=60480/seed) | 0.881498 ± 0.012830 (N(seed0–3)=[57131,56796,57043,56427]) | 0.525488 ± 0.050323 (N(seed0–3)=[3349,3684,3437,4053]) | 0.957705 ± 0.017402 (N=45360/seed) |
| dependence_only | 2 | PhysioGraph (SSM) | 0.842183 ± 0.038643 (N=60480/seed) | 0.867850 ± 0.040745 (N(seed0–3)=[57131,56796,57043,56427]) | 0.445088 ± 0.121854 (N(seed0–3)=[3349,3684,3437,4053]) | 0.964903 ± 0.015687 (N=45360/seed) |
| dependence_only | 3 | Control-GRU | 0.842357 ± 0.031894 (N=60480/seed) | 0.858365 ± 0.033766 (N(seed0–3)=[57131,56796,57043,56427]) | 0.589037 ± 0.052481 (N(seed0–3)=[3349,3684,3437,4053]) | 0.965079 ± 0.034324 (N=45360/seed) |
| dependence_only | 3 | CRN-lite | 0.844936 ± 0.027288 (N=60480/seed) | 0.862252 ± 0.027849 (N(seed0–3)=[57131,56796,57043,56427]) | 0.570582 ± 0.052397 (N(seed0–3)=[3349,3684,3437,4053]) | 0.963084 ± 0.037031 (N=45360/seed) |
| dependence_only | 3 | PhysioGraph-GRU | 0.847445 ± 0.026146 (N=60480/seed) | 0.864522 ± 0.029169 (N(seed0–3)=[57131,56796,57043,56427]) | 0.577757 ± 0.053382 (N(seed0–3)=[3349,3684,3437,4053]) | 0.946412 ± 0.031070 (N=45360/seed) |
| dependence_only | 3 | PhysioGraph (SSM) | 0.801918 ± 0.038754 (N=60480/seed) | 0.816929 ± 0.042084 (N(seed0–3)=[57131,56796,57043,56427]) | 0.574563 ± 0.151871 (N(seed0–3)=[3349,3684,3437,4053]) | 0.934568 ± 0.028170 (N=45360/seed) |
| dependence_only | 4 | Control-GRU | 0.767613 ± 0.056818 (N=60480/seed) | 0.775208 ± 0.060279 (N(seed0–3)=[57131,56796,57043,56427]) | 0.649567 ± 0.061000 (N(seed0–3)=[3349,3684,3437,4053]) | 0.907474 ± 0.062946 (N=45360/seed) |
| dependence_only | 4 | CRN-lite | 0.772640 ± 0.053379 (N=60480/seed) | 0.781781 ± 0.054135 (N(seed0–3)=[57131,56796,57043,56427]) | 0.628150 ± 0.080188 (N(seed0–3)=[3349,3684,3437,4053]) | 0.908868 ± 0.069225 (N=45360/seed) |
| dependence_only | 4 | PhysioGraph-GRU | 0.778956 ± 0.030356 (N=60480/seed) | 0.787241 ± 0.033446 (N(seed0–3)=[57131,56796,57043,56427]) | 0.651075 ± 0.032576 (N(seed0–3)=[3349,3684,3437,4053]) | 0.894841 ± 0.042918 (N=45360/seed) |
| dependence_only | 4 | PhysioGraph (SSM) | 0.739641 ± 0.032221 (N=60480/seed) | 0.748406 ± 0.036977 (N(seed0–3)=[57131,56796,57043,56427]) | 0.605445 ± 0.150093 (N(seed0–3)=[3349,3684,3437,4053]) | 0.890757 ± 0.049789 (N=45360/seed) |

## Physical-unit RMSE: four-seed means ± sd

Each channel is computed from 12600 values per run. Source: `main_aggregates[*].rmse_by_channel`, derived from each listed run's `metrics.rmse_by_channel`. Channel labels include their physical units.

| Family | Point | Model | MAP (mmHg) | HR (beats/min) | CO (L/min) | CVP (mmHg) | UO (mL/min) | Lac (mmol/L) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| support_only | 0 | Control-GRU | 8.044895 ± 0.366576 | 4.444348 ± 0.326515 | 0.142875 ± 0.025176 | 0.588950 ± 0.045920 | 0.163229 ± 0.019842 | 0.823616 ± 0.056927 |
| support_only | 0 | CRN-lite | 8.018600 ± 0.390121 | 4.465326 ± 0.342943 | 0.144297 ± 0.018105 | 0.583690 ± 0.042147 | 0.163790 ± 0.020171 | 0.819863 ± 0.058417 |
| support_only | 0 | PhysioGraph-GRU | 7.991532 ± 0.572253 | 4.521441 ± 0.404813 | 0.148112 ± 0.010545 | 0.638293 ± 0.037707 | 0.154671 ± 0.011978 | 0.820704 ± 0.056781 |
| support_only | 0 | PhysioGraph (SSM) | 8.393692 ± 0.272216 | 5.162232 ± 0.504676 | 0.319760 ± 0.094546 | 1.115024 ± 0.282102 | 0.170113 ± 0.015740 | 0.808656 ± 0.061847 |
| support_only | 1 | Control-GRU | 8.076016 ± 0.395677 | 4.424047 ± 0.381011 | 0.137709 ± 0.021999 | 0.585402 ± 0.043384 | 0.164552 ± 0.021131 | 0.830752 ± 0.067725 |
| support_only | 1 | CRN-lite | 8.062896 ± 0.429132 | 4.442231 ± 0.382132 | 0.136597 ± 0.018545 | 0.584207 ± 0.043020 | 0.165345 ± 0.021580 | 0.829628 ± 0.070190 |
| support_only | 1 | PhysioGraph-GRU | 7.848374 ± 0.427245 | 4.426134 ± 0.270569 | 0.141981 ± 0.010281 | 0.643504 ± 0.040380 | 0.154692 ± 0.011964 | 0.838119 ± 0.080586 |
| support_only | 1 | PhysioGraph (SSM) | 9.098092 ± 0.559090 | 5.431181 ± 0.878787 | 0.292407 ± 0.094143 | 1.249957 ± 0.535716 | 0.173678 ± 0.014427 | 0.857904 ± 0.117784 |
| support_only | 2 | Control-GRU | 7.729254 ± 0.264976 | 4.180039 ± 0.318034 | 0.124771 ± 0.022516 | 0.587921 ± 0.043549 | 0.158696 ± 0.018505 | 0.807775 ± 0.059971 |
| support_only | 2 | CRN-lite | 7.699862 ± 0.269983 | 4.200811 ± 0.318429 | 0.126559 ± 0.016951 | 0.583614 ± 0.044061 | 0.159270 ± 0.018396 | 0.807210 ± 0.059730 |
| support_only | 2 | PhysioGraph-GRU | 7.718999 ± 0.411282 | 4.404482 ± 0.436396 | 0.139464 ± 0.017188 | 0.638999 ± 0.034141 | 0.150300 ± 0.016319 | 0.822251 ± 0.084267 |
| support_only | 2 | PhysioGraph (SSM) | 8.801192 ± 0.363762 | 4.906760 ± 0.561471 | 0.303029 ± 0.117576 | 1.054237 ± 0.227767 | 0.168876 ± 0.026324 | 0.859582 ± 0.092542 |
| support_only | 3 | Control-GRU | 7.227459 ± 0.158575 | 3.953886 ± 0.258030 | 0.117894 ± 0.021131 | 0.589814 ± 0.050820 | 0.149154 ± 0.015297 | 0.783880 ± 0.048790 |
| support_only | 3 | CRN-lite | 7.241163 ± 0.189937 | 3.976120 ± 0.264909 | 0.117203 ± 0.018006 | 0.585541 ± 0.048511 | 0.151143 ± 0.016919 | 0.785926 ± 0.052416 |
| support_only | 3 | PhysioGraph-GRU | 7.267198 ± 0.656098 | 3.992488 ± 0.425739 | 0.122673 ± 0.014906 | 0.609036 ± 0.042651 | 0.141844 ± 0.022474 | 0.790646 ± 0.091453 |
| support_only | 3 | PhysioGraph (SSM) | 8.471592 ± 1.061835 | 4.824236 ± 0.458893 | 0.313352 ± 0.108373 | 1.063958 ± 0.204565 | 0.164580 ± 0.011669 | 0.833774 ± 0.064917 |
| support_only | 4 | Control-GRU | 6.912284 ± 0.205368 | 3.851167 ± 0.254504 | 0.113521 ± 0.021530 | 0.587846 ± 0.054190 | 0.143170 ± 0.014853 | 0.777663 ± 0.045784 |
| support_only | 4 | CRN-lite | 6.886728 ± 0.179574 | 3.818133 ± 0.211853 | 0.112729 ± 0.015254 | 0.586296 ± 0.053936 | 0.144236 ± 0.014327 | 0.777539 ± 0.045323 |
| support_only | 4 | PhysioGraph-GRU | 7.116292 ± 0.586907 | 3.998217 ± 0.414311 | 0.118026 ± 0.010988 | 0.622588 ± 0.027844 | 0.141388 ± 0.015088 | 0.822787 ± 0.088218 |
| support_only | 4 | PhysioGraph (SSM) | 8.246643 ± 1.212941 | 4.636698 ± 0.319956 | 0.312861 ± 0.128687 | 1.075086 ± 0.235066 | 0.158877 ± 0.014031 | 0.846380 ± 0.054214 |
| dependence_only | 0 | Control-GRU | 6.816697 ± 0.394856 | 3.850646 ± 0.341369 | 0.110601 ± 0.018103 | 0.570545 ± 0.048275 | 0.137734 ± 0.016884 | 0.772161 ± 0.053640 |
| dependence_only | 0 | CRN-lite | 6.808951 ± 0.398831 | 3.810761 ± 0.320850 | 0.111574 ± 0.014811 | 0.574005 ± 0.041350 | 0.138622 ± 0.017516 | 0.768840 ± 0.054726 |
| dependence_only | 0 | PhysioGraph-GRU | 7.059285 ± 0.632976 | 3.991313 ± 0.411275 | 0.112004 ± 0.014743 | 0.609024 ± 0.036656 | 0.136876 ± 0.012208 | 0.785414 ± 0.063797 |
| dependence_only | 0 | PhysioGraph (SSM) | 8.017793 ± 0.912817 | 4.886666 ± 0.666229 | 0.300450 ± 0.099821 | 0.994534 ± 0.118354 | 0.150690 ± 0.013650 | 0.799839 ± 0.047978 |
| dependence_only | 1 | Control-GRU | 6.798226 ± 0.361745 | 3.835371 ± 0.322819 | 0.111046 ± 0.018268 | 0.575910 ± 0.050826 | 0.137613 ± 0.016740 | 0.770941 ± 0.051711 |
| dependence_only | 1 | CRN-lite | 6.784313 ± 0.348444 | 3.802256 ± 0.309959 | 0.111220 ± 0.015041 | 0.578016 ± 0.044655 | 0.138594 ± 0.017144 | 0.767451 ± 0.050659 |
| dependence_only | 1 | PhysioGraph-GRU | 7.010903 ± 0.641987 | 3.928183 ± 0.403822 | 0.110317 ± 0.013838 | 0.611761 ± 0.050124 | 0.138829 ± 0.017309 | 0.778401 ± 0.072245 |
| dependence_only | 1 | PhysioGraph (SSM) | 7.772146 ± 0.377452 | 4.996811 ± 0.523634 | 0.296829 ± 0.095850 | 1.080827 ± 0.252501 | 0.149754 ± 0.014149 | 0.799511 ± 0.068380 |
| dependence_only | 2 | Control-GRU | 6.793035 ± 0.321389 | 3.823768 ± 0.300819 | 0.112150 ± 0.018851 | 0.579797 ± 0.053480 | 0.137953 ± 0.016057 | 0.770372 ± 0.048848 |
| dependence_only | 2 | CRN-lite | 6.767699 ± 0.282613 | 3.792557 ± 0.285398 | 0.111408 ± 0.014668 | 0.581004 ± 0.048211 | 0.138939 ± 0.016351 | 0.766530 ± 0.046641 |
| dependence_only | 2 | PhysioGraph-GRU | 6.941475 ± 0.710736 | 3.946363 ± 0.487557 | 0.115996 ± 0.019100 | 0.648501 ± 0.090743 | 0.136328 ± 0.016328 | 0.790698 ± 0.088854 |
| dependence_only | 2 | PhysioGraph (SSM) | 7.338295 ± 0.573855 | 4.676050 ± 0.148346 | 0.297873 ± 0.079615 | 1.332591 ± 0.314090 | 0.142756 ± 0.012314 | 0.786415 ± 0.039062 |
| dependence_only | 3 | Control-GRU | 6.813074 ± 0.270197 | 3.826313 ± 0.280492 | 0.112262 ± 0.020416 | 0.582345 ± 0.053781 | 0.139342 ± 0.015315 | 0.771807 ± 0.046916 |
| dependence_only | 3 | CRN-lite | 6.795670 ± 0.228003 | 3.799954 ± 0.259150 | 0.111209 ± 0.015052 | 0.584777 ± 0.050965 | 0.140500 ± 0.015306 | 0.769546 ± 0.044698 |
| dependence_only | 3 | PhysioGraph-GRU | 7.118019 ± 0.580155 | 3.963568 ± 0.415721 | 0.126397 ± 0.022008 | 0.674035 ± 0.067488 | 0.141461 ± 0.016104 | 0.793178 ± 0.064908 |
| dependence_only | 3 | PhysioGraph (SSM) | 7.573007 ± 0.620685 | 4.634394 ± 0.195660 | 0.295410 ± 0.099951 | 1.351397 ± 0.724748 | 0.150451 ± 0.011877 | 0.773326 ± 0.046500 |
| dependence_only | 4 | Control-GRU | 6.912284 ± 0.205368 | 3.851167 ± 0.254504 | 0.113521 ± 0.021530 | 0.587846 ± 0.054190 | 0.143170 ± 0.014853 | 0.777663 ± 0.045784 |
| dependence_only | 4 | CRN-lite | 6.886728 ± 0.179574 | 3.818133 ± 0.211853 | 0.112729 ± 0.015254 | 0.586296 ± 0.053936 | 0.144236 ± 0.014327 | 0.777539 ± 0.045323 |
| dependence_only | 4 | PhysioGraph-GRU | 7.116292 ± 0.586907 | 3.998217 ± 0.414311 | 0.118026 ± 0.010988 | 0.622588 ± 0.027844 | 0.141388 ± 0.015088 | 0.822787 ± 0.088218 |
| dependence_only | 4 | PhysioGraph (SSM) | 8.246643 ± 1.212941 | 4.636698 ± 0.319956 | 0.312861 ± 0.128687 | 1.075086 ± 0.235066 | 0.158877 ± 0.014031 | 0.846380 ± 0.054214 |

Paired RMSE differences below use A minus Control-GRU; negative means lower error. Each channel cell contains mean [95% paired t CI]; all use four seed pairs. Per-channel sign counts and seed differences are in `main_paired_differences[*].rmse_by_channel`.

| Family | Point | A − Control-GRU | MAP (mmHg) | HR (beats/min) | CO (L/min) | CVP (mmHg) | UO (mL/min) | Lac (mmol/L) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| support_only | 0 | CRN-lite | -0.026295 [-0.104323, 0.051732] {1/0/3} | 0.020978 [-0.075036, 0.116993] {2/0/2} | 0.001422 [-0.009923, 0.012766] {2/0/2} | -0.005259 [-0.015214, 0.004695] {1/0/3} | 0.000561 [-0.000078, 0.001200] {4/0/0} | -0.003752 [-0.007700, 0.000195] {0/0/4} |
| support_only | 0 | PhysioGraph-GRU | -0.053363 [-0.834795, 0.728069] {2/0/2} | 0.077093 [-0.411237, 0.565422] {2/0/2} | 0.005237 [-0.026511, 0.036985] {3/0/1} | 0.049344 [-0.020743, 0.119430] {3/0/1} | -0.008559 [-0.022638, 0.005521] {1/0/3} | -0.002912 [-0.113904, 0.108080] {1/0/3} |
| support_only | 0 | PhysioGraph (SSM) | 0.348797 [-0.580906, 1.278500] {3/0/1} | 0.717884 [-0.050432, 1.486201] {4/0/0} | 0.176885 [0.044612, 0.309157] {4/0/0} | 0.526074 [0.025415, 1.026733] {4/0/0} | 0.006883 [-0.010553, 0.024320] {3/0/1} | -0.014959 [-0.044684, 0.014766] {1/0/3} |
| support_only | 1 | CRN-lite | -0.013120 [-0.080731, 0.054490] {2/0/2} | 0.018184 [-0.030103, 0.066470] {3/0/1} | -0.001112 [-0.010426, 0.008202] {1/0/3} | -0.001195 [-0.007307, 0.004918] {2/0/2} | 0.000793 [-0.000258, 0.001844] {3/0/1} | -0.001124 [-0.006021, 0.003773] {2/0/2} |
| support_only | 1 | PhysioGraph-GRU | -0.227641 [-0.979242, 0.523959] {1/0/3} | 0.002086 [-0.488851, 0.493024] {3/0/1} | 0.004272 [-0.020795, 0.029339] {3/0/1} | 0.058102 [-0.007344, 0.123548] {3/0/1} | -0.009861 [-0.025602, 0.005880] {0/0/4} | 0.007367 [-0.047251, 0.061985] {2/0/2} |
| support_only | 1 | PhysioGraph (SSM) | 1.022076 [-0.449772, 2.493924] {4/0/0} | 1.007134 [-0.233556, 2.247824] {4/0/0} | 0.154698 [0.010975, 0.298421] {4/0/0} | 0.664555 [-0.242805, 1.571915] {4/0/0} | 0.009125 [-0.003447, 0.021697] {3/0/1} | 0.027152 [-0.154200, 0.208503] {2/0/2} |
| support_only | 2 | CRN-lite | -0.029393 [-0.100383, 0.041598] {1/0/3} | 0.020771 [-0.032397, 0.073940] {3/0/1} | 0.001788 [-0.009094, 0.012670] {3/0/1} | -0.004307 [-0.019426, 0.010812] {2/0/2} | 0.000574 [-0.001486, 0.002635] {2/0/2} | -0.000565 [-0.010707, 0.009577] {2/0/2} |
| support_only | 2 | PhysioGraph-GRU | -0.010255 [-0.390475, 0.369964] {2/0/2} | 0.224443 [0.022723, 0.426163] {4/0/0} | 0.014693 [-0.009575, 0.038961] {3/0/1} | 0.051078 [0.002751, 0.099405] {4/0/0} | -0.008396 [-0.012726, -0.004066] {0/0/4} | 0.014476 [-0.027344, 0.056296] {3/0/1} |
| support_only | 2 | PhysioGraph (SSM) | 1.071937 [0.279118, 1.864757] {4/0/0} | 0.726721 [0.028722, 1.424720] {4/0/0} | 0.178258 [-0.010016, 0.366532] {4/0/0} | 0.466316 [0.106500, 0.826132] {4/0/0} | 0.010180 [-0.005447, 0.025808] {4/0/0} | 0.051808 [-0.005394, 0.109009] {4/0/0} |
| support_only | 3 | CRN-lite | 0.013704 [-0.096332, 0.123740] {1/0/3} | 0.022234 [-0.055736, 0.100204] {3/0/1} | -0.000691 [-0.010713, 0.009331] {2/0/2} | -0.004272 [-0.020214, 0.011670] {2/0/2} | 0.001989 [-0.001640, 0.005619] {3/0/1} | 0.002046 [-0.009310, 0.013402] {2/0/2} |
| support_only | 3 | PhysioGraph-GRU | 0.039739 [-0.799110, 0.878587] {2/0/2} | 0.038602 [-0.239558, 0.316763] {2/0/2} | 0.004779 [-0.019786, 0.029344] {3/0/1} | 0.019223 [-0.045191, 0.083636] {2/0/2} | -0.007310 [-0.019912, 0.005292] {1/0/3} | 0.006766 [-0.071198, 0.084730] {2/0/2} |
| support_only | 3 | PhysioGraph (SSM) | 1.244133 [-0.694814, 3.183080] {4/0/0} | 0.870350 [0.177717, 1.562983] {4/0/0} | 0.195458 [0.031048, 0.359868] {4/0/0} | 0.474145 [0.104875, 0.843415] {4/0/0} | 0.015426 [-0.003171, 0.034024] {4/0/0} | 0.049894 [-0.001874, 0.101662] {4/0/0} |
| support_only | 4 | CRN-lite | -0.025556 [-0.196689, 0.145577] {2/0/2} | -0.033035 [-0.111539, 0.045470] {2/0/2} | -0.000792 [-0.011510, 0.009926] {2/0/2} | -0.001550 [-0.023962, 0.020862] {3/0/1} | 0.001066 [-0.002495, 0.004628] {2/0/2} | -0.000123 [-0.007328, 0.007081] {2/0/2} |
| support_only | 4 | PhysioGraph-GRU | 0.204008 [-0.524655, 0.932671] {2/0/2} | 0.147050 [-0.193509, 0.487609] {3/0/1} | 0.004505 [-0.021169, 0.030179] {2/0/2} | 0.034742 [-0.059652, 0.129137] {3/0/1} | -0.001782 [-0.007268, 0.003704] {1/0/3} | 0.045124 [-0.083443, 0.173691] {3/0/1} |
| support_only | 4 | PhysioGraph (SSM) | 1.334359 [-0.894262, 3.562980] {4/0/0} | 0.785531 [0.480705, 1.090357] {4/0/0} | 0.199341 [-0.001744, 0.400425] {4/0/0} | 0.487240 [0.035369, 0.939110] {4/0/0} | 0.015706 [-0.010742, 0.042155] {4/0/0} | 0.068717 [-0.004839, 0.142272] {4/0/0} |
| dependence_only | 0 | CRN-lite | -0.007745 [-0.120652, 0.105161] {2/0/2} | -0.039885 [-0.146187, 0.066416] {2/0/2} | 0.000972 [-0.004778, 0.006723] {3/0/1} | 0.003460 [-0.028773, 0.035693] {3/0/1} | 0.000888 [-0.001151, 0.002926] {3/0/1} | -0.003321 [-0.008487, 0.001846] {1/0/3} |
| dependence_only | 0 | PhysioGraph-GRU | 0.242588 [-0.361331, 0.846508] {3/0/1} | 0.140667 [-0.003782, 0.285117] {4/0/0} | 0.001403 [-0.012302, 0.015107] {3/0/1} | 0.038479 [-0.032247, 0.109205] {3/0/1} | -0.000858 [-0.009498, 0.007781] {2/0/2} | 0.013253 [-0.026686, 0.053193] {3/0/1} |
| dependence_only | 0 | PhysioGraph (SSM) | 1.201096 [-0.401168, 2.803360] {4/0/0} | 1.036020 [0.052374, 2.019666] {4/0/0} | 0.189849 [0.030645, 0.349054] {4/0/0} | 0.423989 [0.192337, 0.655641] {4/0/0} | 0.012956 [0.002655, 0.023256] {4/0/0} | 0.027678 [-0.034219, 0.089576] {3/0/1} |
| dependence_only | 1 | CRN-lite | -0.013913 [-0.081630, 0.053805] {2/0/2} | -0.033115 [-0.126581, 0.060351] {1/0/3} | 0.000174 [-0.006050, 0.006397] {3/0/1} | 0.002106 [-0.030278, 0.034490] {3/0/1} | 0.000981 [-0.001020, 0.002981] {3/0/1} | -0.003490 [-0.005795, -0.001186] {0/0/4} |
| dependence_only | 1 | PhysioGraph-GRU | 0.212677 [-0.348750, 0.774103] {3/0/1} | 0.092812 [-0.041327, 0.226951] {3/0/1} | -0.000730 [-0.009740, 0.008281] {2/0/2} | 0.035852 [-0.031482, 0.103185] {3/0/1} | 0.001216 [-0.004848, 0.007280] {3/0/1} | 0.007460 [-0.044049, 0.058970] {2/0/2} |
| dependence_only | 1 | PhysioGraph (SSM) | 0.973920 [0.353931, 1.593909] {4/0/0} | 1.161440 [0.104959, 2.217922] {4/0/0} | 0.185783 [0.036819, 0.334746] {4/0/0} | 0.504918 [0.058644, 0.951192] {4/0/0} | 0.012141 [0.003570, 0.020711] {4/0/0} | 0.028570 [-0.037204, 0.094344] {3/0/1} |
| dependence_only | 2 | CRN-lite | -0.025336 [-0.093317, 0.042644] {2/0/2} | -0.031210 [-0.105557, 0.043136] {2/0/2} | -0.000742 [-0.008914, 0.007430] {2/0/2} | 0.001207 [-0.027055, 0.029469] {3/0/1} | 0.000986 [-0.001442, 0.003414] {3/0/1} | -0.003842 [-0.007995, 0.000311] {0/0/4} |
| dependence_only | 2 | PhysioGraph-GRU | 0.148439 [-0.628539, 0.925418] {2/0/2} | 0.122596 [-0.237749, 0.482941] {2/0/2} | 0.003846 [-0.009530, 0.017221] {3/0/1} | 0.068704 [-0.039097, 0.176505] {3/0/1} | -0.001626 [-0.008752, 0.005500] {1/0/3} | 0.020327 [-0.103099, 0.143752] {2/0/2} |
| dependence_only | 2 | PhysioGraph (SSM) | 0.545260 [-0.270474, 1.360993] {4/0/0} | 0.852282 [0.561447, 1.143118] {4/0/0} | 0.185723 [0.064805, 0.306641] {4/0/0} | 0.752794 [0.204456, 1.301131] {4/0/0} | 0.004803 [-0.005319, 0.014924] {2/0/2} | 0.016043 [-0.025608, 0.057695] {3/0/1} |
| dependence_only | 3 | CRN-lite | -0.017404 [-0.116005, 0.081198] {2/0/2} | -0.026359 [-0.083883, 0.031166] {1/0/3} | -0.001053 [-0.010613, 0.008507] {2/0/2} | 0.002432 [-0.021592, 0.026456] {3/0/1} | 0.001158 [-0.001760, 0.004075] {3/0/1} | -0.002261 [-0.008028, 0.003505] {1/0/3} |
| dependence_only | 3 | PhysioGraph-GRU | 0.304946 [-0.298491, 0.908383] {3/0/1} | 0.137255 [-0.129336, 0.403847] {3/0/1} | 0.014135 [-0.021769, 0.050039] {3/0/1} | 0.091691 [-0.045927, 0.229309] {3/0/1} | 0.002119 [-0.010185, 0.014423] {2/0/2} | 0.021371 [-0.057016, 0.099758] {2/0/2} |
| dependence_only | 3 | PhysioGraph (SSM) | 0.759933 [-0.566838, 2.086704] {4/0/0} | 0.808081 [0.229008, 1.387154] {4/0/0} | 0.183148 [0.026706, 0.339590] {4/0/0} | 0.769052 [-0.453208, 1.991313] {4/0/0} | 0.011109 [-0.013018, 0.035235] {3/0/1} | 0.001519 [-0.031967, 0.035004] {3/0/1} |
| dependence_only | 4 | CRN-lite | -0.025556 [-0.196689, 0.145577] {2/0/2} | -0.033035 [-0.111539, 0.045470] {2/0/2} | -0.000792 [-0.011510, 0.009926] {2/0/2} | -0.001550 [-0.023962, 0.020862] {3/0/1} | 0.001066 [-0.002495, 0.004628] {2/0/2} | -0.000123 [-0.007328, 0.007081] {2/0/2} |
| dependence_only | 4 | PhysioGraph-GRU | 0.204008 [-0.524655, 0.932671] {2/0/2} | 0.147050 [-0.193509, 0.487609] {3/0/1} | 0.004505 [-0.021169, 0.030179] {2/0/2} | 0.034742 [-0.059652, 0.129137] {3/0/1} | -0.001782 [-0.007268, 0.003704] {1/0/3} | 0.045124 [-0.083443, 0.173691] {3/0/1} |
| dependence_only | 4 | PhysioGraph (SSM) | 1.334359 [-0.894262, 3.562980] {4/0/0} | 0.785531 [0.480705, 1.090357] {4/0/0} | 0.199341 [-0.001744, 0.400425] {4/0/0} | 0.487240 [0.035369, 0.939110] {4/0/0} | 0.015706 [-0.010742, 0.042155] {4/0/0} | 0.068717 [-0.004839, 0.142272] {4/0/0} |

Diagnostic RMSE means ± sample sd, in the same physical units:

| λ | Epochs | MAP (mmHg) | HR (beats/min) | CO (L/min) | CVP (mmHg) | UO (mL/min) | Lac (mmol/L) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.000000 | 60 | 7.375290 ± 0.473244 | 4.155311 ± 0.298682 | 0.125106 ± 0.012667 | 0.852297 ± 0.195044 | 0.157231 ± 0.021505 | 0.865855 ± 0.119477 |
| 0.000000 | 120 | 7.309978 ± 0.924369 | 4.563076 ± 0.821553 | 0.225983 ± 0.078429 | 0.998096 ± 0.142753 | 0.157693 ± 0.031506 | 0.890594 ± 0.108843 |
| 0.250000 | 60 | 8.147836 ± 1.063857 | 4.966481 ± 0.666415 | 0.233668 ± 0.049162 | 1.259308 ± 0.035847 | 0.165122 ± 0.030223 | 0.981862 ± 0.090913 |
| 0.250000 | 120 | 8.937609 ± 1.094953 | 5.488766 ± 0.775289 | 0.370266 ± 0.133289 | 1.376192 ± 0.231864 | 0.175640 ± 0.042455 | 0.972789 ± 0.164526 |
| 1.000000 | 60 | 9.291517 ± 1.050758 | 5.963437 ± 0.616730 | 0.446865 ± 0.093862 | 2.515463 ± 0.846567 | 0.194328 ± 0.031207 | 1.136508 ± 0.151509 |
| 1.000000 | 120 | 9.860607 ± 1.717969 | 7.899674 ± 1.345260 | 0.609546 ± 0.115852 | 2.037567 ± 0.087830 | 0.195343 ± 0.031648 | 1.059009 ± 0.130369 |

## All main runs: 160 rows

Status `complete` is derived from `finite=true`, the complete epoch history and the matching final completion-log JSON; the source has no native status or host exit-code field. Exact all-cell accuracy equals exact post-effect accuracy because exact zero-effect N=0. Tolerance A/P/Z means all/post-effect/zero-effect. Every accuracy cell includes correct/denominator. RMSE vector order is MAP, HR, CO, CVP, UO, lactate, in the units above. CRN-lite's complete auxiliary distributions are tabulated immediately afterward and stored in each row's `balancing_target.distribution`.

| Family | Point | Model | Seed | Status | Epochs | Exact post-effect | Exact zero-effect | Tolerance A | Tolerance P | Tolerance Z | RMSE vector | Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| support_only | 0 | Control-GRU | 0 | complete | 60 | 0.450678 (27257/60480) | null (0/0) | 0.129315 (7821/60480) | 0.082005 (4685/57131) | 0.936399 (3136/3349) | 7.508884; 3.999770; 0.127815; 0.527403; 0.148190; 0.779739 | [run](main/support_only/point0/control_gru/seed0/run.json) |
| support_only | 0 | Control-GRU | 1 | complete | 60 | 0.270403 (16354/60480) | null (0/0) | 0.118072 (7141/60480) | 0.066959 (3803/56796) | 0.906080 (3338/3684) | 8.129817; 4.597787; 0.172846; 0.601674; 0.148860; 0.788282 | [run](main/support_only/point0/control_gru/seed1/run.json) |
| support_only | 0 | Control-GRU | 2 | complete | 60 | 0.331019 (20020/60480) | null (0/0) | 0.167295 (10118/60480) | 0.129078 (7363/57043) | 0.801571 (2755/3437) | 8.329071; 4.757640; 0.117182; 0.589027; 0.190504; 0.904520 | [run](main/support_only/point0/control_gru/seed2/run.json) |
| support_only | 0 | Control-GRU | 3 | complete | 60 | 0.335830 (20311/60480) | null (0/0) | 0.158995 (9616/60480) | 0.108955 (6148/56427) | 0.855662 (3468/4053) | 8.211806; 4.422193; 0.153657; 0.637695; 0.165364; 0.821921 | [run](main/support_only/point0/control_gru/seed3/run.json) |
| support_only | 0 | CRN-lite | 0 | complete | 60 | 0.417791 (25268/60480) | null (0/0) | 0.097354 (5888/60480) | 0.046770 (2672/57131) | 0.960287 (3216/3349) | 7.456888; 4.035238; 0.134258; 0.529950; 0.148202; 0.775500 | [run](main/support_only/point0/crn_lite/seed0/run.json) |
| support_only | 0 | CRN-lite | 1 | complete | 60 | 0.284954 (17234/60480) | null (0/0) | 0.120486 (7287/60480) | 0.069477 (3946/56796) | 0.906895 (3341/3684) | 8.124393; 4.565429; 0.166295; 0.597663; 0.149424; 0.785057 | [run](main/support_only/point0/crn_lite/seed1/run.json) |
| support_only | 0 | CRN-lite | 2 | complete | 60 | 0.330870 (20011/60480) | null (0/0) | 0.172305 (10421/60480) | 0.134092 (7649/57043) | 0.806517 (2772/3437) | 8.360444; 4.857681; 0.125527; 0.576603; 0.191467; 0.903744 | [run](main/support_only/point0/crn_lite/seed2/run.json) |
| support_only | 0 | CRN-lite | 3 | complete | 60 | 0.335780 (20308/60480) | null (0/0) | 0.171181 (10353/60480) | 0.123008 (6941/56427) | 0.841846 (3412/4053) | 8.132674; 4.402957; 0.151107; 0.630546; 0.166068; 0.815153 | [run](main/support_only/point0/crn_lite/seed3/run.json) |
| support_only | 0 | PhysioGraph-GRU | 0 | complete | 60 | 0.344577 (20840/60480) | null (0/0) | 0.084077 (5085/60480) | 0.030386 (1736/57131) | 1.000000 (3349/3349) | 7.388603; 4.203854; 0.134014; 0.603284; 0.141914; 0.744459 | [run](main/support_only/point0/physiograph_gru/seed0/run.json) |
| support_only | 0 | PhysioGraph-GRU | 1 | complete | 60 | 0.207837 (12570/60480) | null (0/0) | 0.064286 (3888/60480) | 0.004983 (283/56796) | 0.978556 (3605/3684) | 8.649589; 5.045762; 0.153473; 0.691845; 0.149815; 0.881052 | [run](main/support_only/point0/physiograph_gru/seed1/run.json) |
| support_only | 0 | PhysioGraph-GRU | 2 | complete | 60 | 0.251802 (15229/60480) | null (0/0) | 0.093469 (5653/60480) | 0.043704 (2493/57043) | 0.919406 (3160/3437) | 7.660373; 4.635417; 0.146654; 0.628977; 0.170149; 0.835390 | [run](main/support_only/point0/physiograph_gru/seed2/run.json) |
| support_only | 0 | PhysioGraph-GRU | 3 | complete | 60 | 0.437120 (26437/60480) | null (0/0) | 0.123991 (7499/60480) | 0.061868 (3491/56427) | 0.988897 (4008/4053) | 8.267563; 4.200729; 0.158308; 0.629068; 0.156804; 0.821915 | [run](main/support_only/point0/physiograph_gru/seed3/run.json) |
| support_only | 0 | PhysioGraph (SSM) | 0 | complete | 60 | 0.448049 (27098/60480) | null (0/0) | 0.327943 (19834/60480) | 0.306856 (17531/57131) | 0.687668 (2303/3349) | 8.672202; 4.628600; 0.391856; 1.486011; 0.170983; 0.749077 | [run](main/support_only/point0/physiograph/seed0/run.json) |
| support_only | 0 | PhysioGraph (SSM) | 1 | complete | 60 | 0.355456 (21498/60480) | null (0/0) | 0.179497 (10856/60480) | 0.141049 (8011/56796) | 0.772258 (2845/3684) | 8.467030; 5.056592; 0.361164; 1.120272; 0.154127; 0.797136 | [run](main/support_only/point0/physiograph/seed1/run.json) |
| support_only | 0 | PhysioGraph (SSM) | 2 | complete | 60 | 0.139947 (8464/60480) | null (0/0) | 0.081597 (4935/60480) | 0.034763 (1983/57043) | 0.858889 (2952/3437) | 8.414565; 5.118663; 0.180963; 0.803802; 0.191321; 0.895514 | [run](main/support_only/point0/physiograph/seed2/run.json) |
| support_only | 0 | PhysioGraph (SSM) | 3 | complete | 60 | 0.476620 (28826/60480) | null (0/0) | 0.203687 (12319/60480) | 0.153526 (8663/56427) | 0.902048 (3656/4053) | 8.020969; 5.845073; 0.345057; 1.050010; 0.164019; 0.792899 | [run](main/support_only/point0/physiograph/seed3/run.json) |
| support_only | 1 | Control-GRU | 0 | complete | 60 | 0.528621 (31971/60480) | null (0/0) | 0.189435 (11457/60480) | 0.145858 (8333/57131) | 0.932816 (3124/3349) | 7.529565; 3.948753; 0.118967; 0.528479; 0.149081; 0.780317 | [run](main/support_only/point1/control_gru/seed0/run.json) |
| support_only | 1 | Control-GRU | 1 | complete | 60 | 0.335582 (20296/60480) | null (0/0) | 0.159358 (9638/60480) | 0.112825 (6408/56796) | 0.876764 (3230/3684) | 8.095061; 4.509334; 0.164137; 0.602838; 0.149125; 0.790046 | [run](main/support_only/point1/control_gru/seed1/run.json) |
| support_only | 1 | Control-GRU | 2 | complete | 60 | 0.331862 (20071/60480) | null (0/0) | 0.206382 (12482/60480) | 0.175569 (10015/57043) | 0.717777 (2467/3437) | 8.465477; 4.870325; 0.120215; 0.579428; 0.193873; 0.928312 | [run](main/support_only/point1/control_gru/seed2/run.json) |
| support_only | 1 | Control-GRU | 3 | complete | 60 | 0.349190 (21119/60480) | null (0/0) | 0.189997 (11491/60480) | 0.144222 (8138/56427) | 0.827288 (3353/4053) | 8.213960; 4.367777; 0.147517; 0.630861; 0.166131; 0.824333 | [run](main/support_only/point1/control_gru/seed3/run.json) |
| support_only | 1 | CRN-lite | 0 | complete | 60 | 0.528522 (31965/60480) | null (0/0) | 0.151174 (9143/60480) | 0.104059 (5945/57131) | 0.954912 (3198/3349) | 7.474517; 3.988278; 0.125743; 0.529590; 0.149008; 0.775116 | [run](main/support_only/point1/crn_lite/seed0/run.json) |
| support_only | 1 | CRN-lite | 1 | complete | 60 | 0.337252 (20397/60480) | null (0/0) | 0.166849 (10091/60480) | 0.120977 (6871/56796) | 0.874050 (3220/3684) | 8.102528; 4.490514; 0.157089; 0.596379; 0.149772; 0.788328 | [run](main/support_only/point1/crn_lite/seed1/run.json) |
| support_only | 1 | CRN-lite | 2 | complete | 60 | 0.331481 (20048/60480) | null (0/0) | 0.210003 (12701/60480) | 0.179409 (10234/57043) | 0.717777 (2467/3437) | 8.501800; 4.916529; 0.116818; 0.577859; 0.195058; 0.930035 | [run](main/support_only/point1/crn_lite/seed2/run.json) |
| support_only | 1 | CRN-lite | 3 | complete | 60 | 0.361359 (21855/60480) | null (0/0) | 0.199256 (12051/60480) | 0.154979 (8745/56427) | 0.815692 (3306/4053) | 8.172738; 4.373602; 0.146736; 0.633000; 0.167543; 0.825034 | [run](main/support_only/point1/crn_lite/seed3/run.json) |
| support_only | 1 | PhysioGraph-GRU | 0 | complete | 60 | 0.373760 (22605/60480) | null (0/0) | 0.099041 (5990/60480) | 0.046227 (2641/57131) | 1.000000 (3349/3349) | 7.414240; 4.102976; 0.127344; 0.593202; 0.143358; 0.748730 | [run](main/support_only/point1/physiograph_gru/seed0/run.json) |
| support_only | 1 | PhysioGraph-GRU | 1 | complete | 60 | 0.288492 (17448/60480) | null (0/0) | 0.087533 (5294/60480) | 0.032766 (1861/56796) | 0.931868 (3433/3684) | 8.379877; 4.765016; 0.148305; 0.681973; 0.146774; 0.840010 | [run](main/support_only/point1/physiograph_gru/seed1/run.json) |
| support_only | 1 | PhysioGraph-GRU | 2 | complete | 60 | 0.243965 (14755/60480) | null (0/0) | 0.087963 (5320/60480) | 0.043371 (2474/57043) | 0.828048 (2846/3437) | 7.610076; 4.428917; 0.142373; 0.669564; 0.169464; 0.943757 | [run](main/support_only/point1/physiograph_gru/seed2/run.json) |
| support_only | 1 | PhysioGraph-GRU | 3 | complete | 60 | 0.459706 (27803/60480) | null (0/0) | 0.124884 (7553/60480) | 0.063693 (3594/56427) | 0.976807 (3959/4053) | 7.989304; 4.407625; 0.149902; 0.629277; 0.159170; 0.819979 | [run](main/support_only/point1/physiograph_gru/seed3/run.json) |
| support_only | 1 | PhysioGraph (SSM) | 0 | complete | 60 | 0.503869 (30474/60480) | null (0/0) | 0.411128 (24865/60480) | 0.392922 (22448/57131) | 0.721708 (2417/3349) | 9.711370; 4.702769; 0.375440; 2.042056; 0.166505; 0.770121 | [run](main/support_only/point1/physiograph/seed0/run.json) |
| support_only | 1 | PhysioGraph (SSM) | 1 | complete | 60 | 0.329084 (19903/60480) | null (0/0) | 0.194610 (11770/60480) | 0.155997 (8860/56796) | 0.789902 (2910/3684) | 9.432949; 6.676927; 0.319978; 0.976270; 0.158970; 0.977916 | [run](main/support_only/point1/physiograph/seed1/run.json) |
| support_only | 1 | PhysioGraph (SSM) | 2 | complete | 60 | 0.235268 (14229/60480) | null (0/0) | 0.139302 (8425/60480) | 0.105745 (6032/57043) | 0.696247 (2393/3437) | 8.620477; 5.396700; 0.157050; 0.880588; 0.192275; 0.939235 | [run](main/support_only/point1/physiograph/seed2/run.json) |
| support_only | 1 | PhysioGraph (SSM) | 3 | complete | 60 | 0.562235 (34004/60480) | null (0/0) | 0.261062 (15789/60480) | 0.212629 (11998/56427) | 0.935357 (3791/4053) | 8.627571; 4.948328; 0.317159; 1.100912; 0.176960; 0.744345 | [run](main/support_only/point1/physiograph/seed3/run.json) |
| support_only | 2 | Control-GRU | 0 | complete | 60 | 0.766716 (46371/60480) | null (0/0) | 0.344511 (20836/60480) | 0.311880 (17818/57131) | 0.901165 (3018/3349) | 7.374810; 3.799871; 0.104472; 0.527596; 0.146955; 0.769721 | [run](main/support_only/point2/control_gru/seed0/run.json) |
| support_only | 2 | Control-GRU | 1 | complete | 60 | 0.733664 (44372/60480) | null (0/0) | 0.312864 (18922/60480) | 0.274702 (15602/56796) | 0.901194 (3320/3684) | 7.713923; 4.264054; 0.151309; 0.611894; 0.143892; 0.765771 | [run](main/support_only/point2/control_gru/seed1/run.json) |
| support_only | 2 | Control-GRU | 2 | complete | 60 | 0.360086 (21778/60480) | null (0/0) | 0.249884 (15113/60480) | 0.218011 (12436/57043) | 0.778877 (2677/3437) | 8.004707; 4.560492; 0.107774; 0.585914; 0.184578; 0.894561 | [run](main/support_only/point2/control_gru/seed2/run.json) |
| support_only | 2 | Control-GRU | 3 | complete | 60 | 0.765030 (46269/60480) | null (0/0) | 0.367163 (22206/60480) | 0.334698 (18886/56427) | 0.819146 (3320/4053) | 7.823577; 4.095740; 0.135529; 0.626282; 0.159360; 0.801046 | [run](main/support_only/point2/control_gru/seed3/run.json) |
| support_only | 2 | CRN-lite | 0 | complete | 60 | 0.916832 (55450/60480) | null (0/0) | 0.361128 (21841/60480) | 0.328228 (18752/57131) | 0.922365 (3089/3349) | 7.319819; 3.823224; 0.110250; 0.528383; 0.146892; 0.762876 | [run](main/support_only/point2/crn_lite/seed0/run.json) |
| support_only | 2 | CRN-lite | 1 | complete | 60 | 0.775165 (46882/60480) | null (0/0) | 0.328588 (19873/60480) | 0.291711 (16568/56796) | 0.897123 (3305/3684) | 7.703380; 4.237356; 0.142946; 0.599540; 0.144076; 0.765891 | [run](main/support_only/point2/crn_lite/seed1/run.json) |
| support_only | 2 | CRN-lite | 2 | complete | 60 | 0.379762 (22968/60480) | null (0/0) | 0.251769 (15227/60480) | 0.221465 (12633/57043) | 0.754728 (2594/3437) | 7.929001; 4.597307; 0.113723; 0.573708; 0.184261; 0.891036 | [run](main/support_only/point2/crn_lite/seed2/run.json) |
| support_only | 2 | CRN-lite | 3 | complete | 60 | 0.767708 (46431/60480) | null (0/0) | 0.367659 (22236/60480) | 0.335088 (18908/56427) | 0.821120 (3328/4053) | 7.847247; 4.145356; 0.139317; 0.632827; 0.161852; 0.809036 | [run](main/support_only/point2/crn_lite/seed3/run.json) |
| support_only | 2 | PhysioGraph-GRU | 0 | complete | 60 | 0.779993 (47174/60480) | null (0/0) | 0.223528 (13519/60480) | 0.178257 (10184/57131) | 0.995820 (3335/3349) | 7.285584; 3.932040; 0.116709; 0.598260; 0.141973; 0.757577 | [run](main/support_only/point2/physiograph_gru/seed0/run.json) |
| support_only | 2 | PhysioGraph-GRU | 1 | complete | 60 | 0.740360 (44777/60480) | null (0/0) | 0.240939 (14572/60480) | 0.195630 (11111/56796) | 0.939468 (3461/3684) | 7.844936; 4.470163; 0.145889; 0.681070; 0.136323; 0.779467 | [run](main/support_only/point2/physiograph_gru/seed1/run.json) |
| support_only | 2 | PhysioGraph-GRU | 2 | complete | 60 | 0.620205 (37510/60480) | null (0/0) | 0.143800 (8697/60480) | 0.102046 (5821/57043) | 0.836776 (2876/3437) | 8.230843; 4.969167; 0.137784; 0.644091; 0.173399; 0.944958 | [run](main/support_only/point2/physiograph_gru/seed2/run.json) |
| support_only | 2 | PhysioGraph-GRU | 3 | complete | 60 | 0.827943 (50074/60480) | null (0/0) | 0.362467 (21922/60480) | 0.318394 (17966/56427) | 0.976067 (3956/4053) | 7.514634; 4.246560; 0.157475; 0.632576; 0.149504; 0.807002 | [run](main/support_only/point2/physiograph_gru/seed3/run.json) |
| support_only | 2 | PhysioGraph (SSM) | 0 | complete | 60 | 0.595387 (36009/60480) | null (0/0) | 0.449983 (27215/60480) | 0.427754 (24438/57131) | 0.829203 (2777/3349) | 9.034481; 4.200149; 0.434451; 1.113390; 0.147050; 0.777163 | [run](main/support_only/point2/physiograph/seed0/run.json) |
| support_only | 2 | PhysioGraph (SSM) | 1 | complete | 60 | 0.602530 (36441/60480) | null (0/0) | 0.396495 (23980/60480) | 0.368036 (20903/56796) | 0.835233 (3077/3684) | 8.862840; 5.574147; 0.321635; 1.272310; 0.157358; 0.816340 | [run](main/support_only/point2/physiograph/seed1/run.json) |
| support_only | 2 | PhysioGraph (SSM) | 2 | complete | 60 | 0.532159 (32185/60480) | null (0/0) | 0.294494 (17811/60480) | 0.277492 (15829/57043) | 0.576666 (1982/3437) | 9.037943; 4.938111; 0.148642; 0.733757; 0.206925; 0.989992 | [run](main/support_only/point2/physiograph/seed2/run.json) |
| support_only | 2 | PhysioGraph (SSM) | 3 | complete | 60 | 0.620288 (37515/60480) | null (0/0) | 0.400711 (24235/60480) | 0.363106 (20489/56427) | 0.924254 (3746/4053) | 8.269503; 4.914635; 0.307388; 1.097493; 0.164172; 0.854834 | [run](main/support_only/point2/physiograph/seed3/run.json) |
| support_only | 3 | Control-GRU | 0 | complete | 60 | 0.995899 (60232/60480) | null (0/0) | 0.710053 (42944/60480) | 0.703856 (40212/57131) | 0.815766 (2732/3349) | 7.014167; 3.646697; 0.096528; 0.522153; 0.140392; 0.752901 | [run](main/support_only/point3/control_gru/seed0/run.json) |
| support_only | 3 | Control-GRU | 1 | complete | 60 | 0.907821 (54905/60480) | null (0/0) | 0.650265 (39328/60480) | 0.638267 (36251/56796) | 0.835233 (3077/3684) | 7.234786; 4.077119; 0.143525; 0.621669; 0.136664; 0.751085 | [run](main/support_only/point3/control_gru/seed1/run.json) |
| support_only | 3 | Control-GRU | 2 | complete | 60 | 0.833333 (50400/60480) | null (0/0) | 0.586210 (35454/60480) | 0.574619 (32778/57043) | 0.778586 (2676/3437) | 7.396319; 4.237263; 0.105346; 0.580200; 0.170811; 0.854963 | [run](main/support_only/point3/control_gru/seed2/run.json) |
| support_only | 3 | Control-GRU | 3 | complete | 60 | 0.905522 (54766/60480) | null (0/0) | 0.700215 (42349/60480) | 0.697928 (39382/56427) | 0.732050 (2967/4053) | 7.264564; 3.854464; 0.126177; 0.635232; 0.148748; 0.776571 | [run](main/support_only/point3/control_gru/seed3/run.json) |
| support_only | 3 | CRN-lite | 0 | complete | 60 | 0.998810 (60408/60480) | null (0/0) | 0.729282 (44107/60480) | 0.723845 (41354/57131) | 0.822036 (2753/3349) | 6.983556; 3.656028; 0.101502; 0.522784; 0.140789; 0.746401 | [run](main/support_only/point3/crn_lite/seed0/run.json) |
| support_only | 3 | CRN-lite | 1 | complete | 60 | 0.888972 (53765/60480) | null (0/0) | 0.670238 (40536/60480) | 0.660575 (37518/56796) | 0.819218 (3018/3684) | 7.212360; 4.035558; 0.135236; 0.602653; 0.136403; 0.750788 | [run](main/support_only/point3/crn_lite/seed1/run.json) |
| support_only | 3 | CRN-lite | 2 | complete | 60 | 0.833218 (50393/60480) | null (0/0) | 0.607854 (36763/60480) | 0.602195 (34351/57043) | 0.701775 (2412/3437) | 7.387631; 4.294288; 0.101925; 0.578475; 0.174163; 0.859713 | [run](main/support_only/point3/crn_lite/seed2/run.json) |
| support_only | 3 | CRN-lite | 3 | complete | 60 | 0.886376 (53608/60480) | null (0/0) | 0.664550 (40192/60480) | 0.657239 (37086/56427) | 0.766346 (3106/4053) | 7.381104; 3.918605; 0.130147; 0.638254; 0.153217; 0.786801 | [run](main/support_only/point3/crn_lite/seed3/run.json) |
| support_only | 3 | PhysioGraph-GRU | 0 | complete | 60 | 0.940642 (56890/60480) | null (0/0) | 0.722057 (43670/60480) | 0.714341 (40811/57131) | 0.853688 (2859/3349) | 6.612045; 3.540869; 0.100536; 0.584110; 0.130998; 0.721576 | [run](main/support_only/point3/physiograph_gru/seed0/run.json) |
| support_only | 3 | PhysioGraph-GRU | 1 | complete | 60 | 0.866601 (52412/60480) | null (0/0) | 0.707622 (42797/60480) | 0.708307 (40229/56796) | 0.697068 (2568/3684) | 7.472608; 4.137479; 0.132023; 0.666799; 0.126085; 0.773889 | [run](main/support_only/point3/physiograph_gru/seed1/run.json) |
| support_only | 3 | PhysioGraph-GRU | 2 | complete | 60 | 0.832970 (50378/60480) | null (0/0) | 0.590691 (35725/60480) | 0.580317 (33103/57043) | 0.762875 (2622/3437) | 8.091585; 4.514427; 0.130978; 0.570704; 0.175088; 0.923993 | [run](main/support_only/point3/physiograph_gru/seed2/run.json) |
| support_only | 3 | PhysioGraph-GRU | 3 | complete | 60 | 0.889864 (53819/60480) | null (0/0) | 0.738641 (44673/60480) | 0.746682 (42133/56427) | 0.626696 (2540/4053) | 6.892553; 3.777179; 0.127155; 0.614532; 0.135203; 0.743126 | [run](main/support_only/point3/physiograph_gru/seed3/run.json) |
| support_only | 3 | PhysioGraph (SSM) | 0 | complete | 60 | 0.868849 (52548/60480) | null (0/0) | 0.665493 (40249/60480) | 0.650943 (37189/57131) | 0.913706 (3060/3349) | 9.973760; 4.504761; 0.386014; 1.310374; 0.149636; 0.765959 | [run](main/support_only/point3/physiograph/seed0/run.json) |
| support_only | 3 | PhysioGraph (SSM) | 1 | complete | 60 | 0.808003 (48868/60480) | null (0/0) | 0.544759 (32947/60480) | 0.523840 (29752/56796) | 0.867264 (3195/3684) | 8.389781; 5.503219; 0.377403; 0.973579; 0.161041; 0.794221 | [run](main/support_only/point3/physiograph/seed1/run.json) |
| support_only | 3 | PhysioGraph (SSM) | 2 | complete | 60 | 0.833333 (50400/60480) | null (0/0) | 0.661921 (40033/60480) | 0.671809 (38322/57043) | 0.497818 (1711/3437) | 7.526287; 4.599525; 0.154149; 0.836813; 0.172861; 0.906372 | [run](main/support_only/point3/physiograph/seed2/run.json) |
| support_only | 3 | PhysioGraph (SSM) | 3 | complete | 60 | 0.851389 (51492/60480) | null (0/0) | 0.563542 (34083/60480) | 0.551704 (31131/56427) | 0.728349 (2952/4053) | 7.996541; 4.689439; 0.335841; 1.135066; 0.174782; 0.868542 | [run](main/support_only/point3/physiograph/seed3/run.json) |
| support_only | 4 | Control-GRU | 0 | complete | 60 | 0.999223 (60433/60480) | null (0/0) | 0.847354 (51248/60480) | 0.857573 (48994/57131) | 0.673037 (2254/3349) | 6.618002; 3.527128; 0.092373; 0.518645; 0.132765; 0.743872 | [run](main/support_only/point4/control_gru/seed0/run.json) |
| support_only | 4 | Control-GRU | 1 | complete | 60 | 0.886806 (53634/60480) | null (0/0) | 0.728356 (44051/60480) | 0.728801 (41393/56796) | 0.721498 (2658/3684) | 7.003760; 4.014573; 0.138613; 0.611101; 0.133362; 0.751496 | [run](main/support_only/point4/control_gru/seed1/run.json) |
| support_only | 4 | Control-GRU | 2 | complete | 60 | 0.857771 (51878/60480) | null (0/0) | 0.725397 (43872/60480) | 0.731571 (41731/57043) | 0.622927 (2141/3437) | 7.087825; 4.089144; 0.099179; 0.575999; 0.164526; 0.844142 | [run](main/support_only/point4/control_gru/seed2/run.json) |
| support_only | 4 | Control-GRU | 3 | complete | 60 | 0.890394 (53851/60480) | null (0/0) | 0.769345 (46530/60480) | 0.782888 (44176/56427) | 0.580804 (2354/4053) | 6.939548; 3.773824; 0.123918; 0.645637; 0.142028; 0.771142 | [run](main/support_only/point4/control_gru/seed3/run.json) |
| support_only | 4 | CRN-lite | 0 | complete | 60 | 0.999653 (60459/60480) | null (0/0) | 0.845734 (51150/60480) | 0.855928 (48900/57131) | 0.671842 (2250/3349) | 6.625786; 3.533498; 0.097871; 0.519893; 0.133811; 0.739761 | [run](main/support_only/point4/crn_lite/seed0/run.json) |
| support_only | 4 | CRN-lite | 1 | complete | 60 | 0.883168 (53414/60480) | null (0/0) | 0.746561 (45152/60480) | 0.749401 (42563/56796) | 0.702769 (2589/3684) | 6.981865; 3.963775; 0.128538; 0.588915; 0.133151; 0.751820 | [run](main/support_only/point4/crn_lite/seed1/run.json) |
| support_only | 4 | CRN-lite | 2 | complete | 60 | 0.835747 (50546/60480) | null (0/0) | 0.722487 (43696/60480) | 0.734691 (41909/57043) | 0.519930 (1787/3437) | 6.915530; 3.994300; 0.101602; 0.584447; 0.163735; 0.841365 | [run](main/support_only/point4/crn_lite/seed2/run.json) |
| support_only | 4 | CRN-lite | 3 | complete | 60 | 0.918700 (55563/60480) | null (0/0) | 0.775777 (46919/60480) | 0.787105 (44414/56427) | 0.618061 (2505/4053) | 7.023730; 3.780958; 0.122903; 0.651929; 0.146248; 0.777213 | [run](main/support_only/point4/crn_lite/seed3/run.json) |
| support_only | 4 | PhysioGraph-GRU | 0 | complete | 60 | 0.948578 (57370/60480) | null (0/0) | 0.807854 (48859/60480) | 0.816982 (46675/57131) | 0.652135 (2184/3349) | 6.495083; 3.509233; 0.101602; 0.635625; 0.126611; 0.726596 | [run](main/support_only/point4/physiograph_gru/seed0/run.json) |
| support_only | 4 | PhysioGraph-GRU | 1 | complete | 60 | 0.878786 (53149/60480) | null (0/0) | 0.770982 (46629/60480) | 0.776410 (44097/56796) | 0.687296 (2532/3684) | 7.872291; 4.476235; 0.124710; 0.646420; 0.135423; 0.913186 | [run](main/support_only/point4/physiograph_gru/seed1/run.json) |
| support_only | 4 | PhysioGraph-GRU | 2 | complete | 60 | 0.853439 (51616/60480) | null (0/0) | 0.739798 (44743/60480) | 0.744807 (42486/57043) | 0.656677 (2257/3437) | 7.231737; 4.157477; 0.123298; 0.582844; 0.162102; 0.880023 | [run](main/support_only/point4/physiograph_gru/seed2/run.json) |
| support_only | 4 | PhysioGraph-GRU | 3 | complete | 60 | 0.905919 (54790/60480) | null (0/0) | 0.797189 (48214/60480) | 0.810764 (45749/56427) | 0.608191 (2465/4053) | 6.866057; 3.849924; 0.122494; 0.625464; 0.141417; 0.771342 | [run](main/support_only/point4/physiograph_gru/seed3/run.json) |
| support_only | 4 | PhysioGraph (SSM) | 0 | complete | 60 | 0.949272 (57412/60480) | null (0/0) | 0.774041 (46814/60480) | 0.777336 (44410/57131) | 0.717826 (2404/3349) | 9.979146; 4.291005; 0.427857; 1.408251; 0.172144; 0.880348 | [run](main/support_only/point4/physiograph/seed0/run.json) |
| support_only | 4 | PhysioGraph (SSM) | 1 | complete | 60 | 0.868800 (52545/60480) | null (0/0) | 0.699206 (42288/60480) | 0.695806 (39519/56796) | 0.751629 (2769/3684) | 8.183687; 5.056211; 0.357517; 1.061149; 0.140138; 0.792181 | [run](main/support_only/point4/physiograph/seed1/run.json) |
| support_only | 4 | PhysioGraph (SSM) | 2 | complete | 60 | 0.836491 (50591/60480) | null (0/0) | 0.754448 (45629/60480) | 0.770682 (43962/57043) | 0.485016 (1667/3437) | 7.496863; 4.666481; 0.128827; 0.958016; 0.166537; 0.904042 | [run](main/support_only/point4/physiograph/seed2/run.json) |
| support_only | 4 | PhysioGraph (SSM) | 3 | complete | 60 | 0.907358 (54877/60480) | null (0/0) | 0.730870 (44203/60480) | 0.749801 (42309/56427) | 0.467308 (1894/4053) | 7.326874; 4.533096; 0.337245; 0.872925; 0.156688; 0.808948 | [run](main/support_only/point4/physiograph/seed3/run.json) |
| dependence_only | 0 | Control-GRU | 0 | complete | 60 | 0.996197 (60250/60480) | null (0/0) | 0.892030 (53950/60480) | 0.920849 (52609/57131) | 0.400418 (1341/3349) | 6.354081; 3.441251; 0.090221; 0.502215; 0.124781; 0.738814 | [run](main/dependence_only/point0/control_gru/seed0/run.json) |
| dependence_only | 0 | Control-GRU | 1 | complete | 60 | 0.997817 (60348/60480) | null (0/0) | 0.881531 (53315/60480) | 0.913233 (51868/56796) | 0.392780 (1447/3684) | 7.039592; 4.095231; 0.132056; 0.598950; 0.131114; 0.744994 | [run](main/dependence_only/point0/control_gru/seed1/run.json) |
| dependence_only | 0 | Control-GRU | 2 | complete | 60 | 0.993320 (60076/60480) | null (0/0) | 0.901240 (54507/60480) | 0.929720 (53034/57043) | 0.428571 (1473/3437) | 7.232619; 4.166066; 0.102753; 0.571553; 0.162555; 0.852172 | [run](main/dependence_only/point0/control_gru/seed2/run.json) |
| dependence_only | 0 | Control-GRU | 3 | complete | 60 | 0.977662 (59129/60480) | null (0/0) | 0.878208 (53114/60480) | 0.902600 (50931/56427) | 0.538613 (2183/4053) | 6.640496; 3.700036; 0.117374; 0.609462; 0.132486; 0.752664 | [run](main/dependence_only/point0/control_gru/seed3/run.json) |
| dependence_only | 0 | CRN-lite | 0 | complete | 60 | 0.996759 (60284/60480) | null (0/0) | 0.889071 (53771/60480) | 0.916613 (52367/57131) | 0.419230 (1404/3349) | 6.390808; 3.446647; 0.094181; 0.515680; 0.125884; 0.738946 | [run](main/dependence_only/point0/crn_lite/seed0/run.json) |
| dependence_only | 0 | CRN-lite | 1 | complete | 60 | 0.998843 (60410/60480) | null (0/0) | 0.904812 (54723/60480) | 0.940207 (53400/56796) | 0.359121 (1323/3684) | 6.949738; 3.960189; 0.127817; 0.575510; 0.130137; 0.739784 | [run](main/dependence_only/point0/crn_lite/seed1/run.json) |
| dependence_only | 0 | CRN-lite | 2 | complete | 60 | 0.985301 (59591/60480) | null (0/0) | 0.899289 (54389/60480) | 0.925390 (52787/57043) | 0.466104 (1602/3437) | 7.296965; 4.173918; 0.105400; 0.594962; 0.164415; 0.850800 | [run](main/dependence_only/point0/crn_lite/seed2/run.json) |
| dependence_only | 0 | CRN-lite | 3 | complete | 60 | 0.983036 (59454/60480) | null (0/0) | 0.875231 (52934/60480) | 0.899782 (50772/56427) | 0.533432 (2162/4053) | 6.598293; 3.662289; 0.118897; 0.609868; 0.134050; 0.745831 | [run](main/dependence_only/point0/crn_lite/seed3/run.json) |
| dependence_only | 0 | PhysioGraph-GRU | 0 | complete | 60 | 0.966253 (58439/60480) | null (0/0) | 0.843783 (51032/60480) | 0.866080 (49480/57131) | 0.463422 (1552/3349) | 6.215546; 3.458751; 0.090986; 0.572660; 0.129328; 0.723825 | [run](main/dependence_only/point0/physiograph_gru/seed0/run.json) |
| dependence_only | 0 | PhysioGraph-GRU | 1 | complete | 60 | 0.969362 (58627/60480) | null (0/0) | 0.881399 (53307/60480) | 0.913709 (51895/56796) | 0.383279 (1412/3684) | 7.735336; 4.327156; 0.121783; 0.646186; 0.128799; 0.789117 | [run](main/dependence_only/point0/physiograph_gru/seed1/run.json) |
| dependence_only | 0 | PhysioGraph-GRU | 2 | complete | 60 | 0.966369 (58446/60480) | null (0/0) | 0.867312 (52455/60480) | 0.899812 (51328/57043) | 0.327902 (1127/3437) | 7.240528; 4.303776; 0.112548; 0.634387; 0.154758; 0.872356 | [run](main/dependence_only/point0/physiograph_gru/seed2/run.json) |
| dependence_only | 0 | PhysioGraph-GRU | 3 | complete | 60 | 0.954349 (57719/60480) | null (0/0) | 0.878770 (53148/60480) | 0.898010 (50672/56427) | 0.610906 (2476/4053) | 7.045729; 3.875570; 0.122699; 0.582864; 0.134619; 0.756358 | [run](main/dependence_only/point0/physiograph_gru/seed3/run.json) |
| dependence_only | 0 | PhysioGraph (SSM) | 0 | complete | 60 | 0.954547 (57731/60480) | null (0/0) | 0.855969 (51769/60480) | 0.875707 (50030/57131) | 0.519259 (1739/3349) | 8.425775; 4.656634; 0.384970; 1.110253; 0.145332; 0.767781 | [run](main/dependence_only/point0/physiograph/seed0/run.json) |
| dependence_only | 0 | PhysioGraph (SSM) | 1 | complete | 60 | 0.956895 (57873/60480) | null (0/0) | 0.839286 (50760/60480) | 0.861240 (48915/56796) | 0.500814 (1845/3684) | 9.101857; 5.880076; 0.342290; 1.060170; 0.138622; 0.827234 | [run](main/dependence_only/point0/physiograph/seed1/run.json) |
| dependence_only | 0 | PhysioGraph (SSM) | 2 | complete | 60 | 0.985152 (59582/60480) | null (0/0) | 0.907722 (54899/60480) | 0.937854 (53498/57043) | 0.407623 (1401/3437) | 7.421696; 4.490277; 0.156600; 0.841090; 0.170192; 0.852751 | [run](main/dependence_only/point0/physiograph/seed2/run.json) |
| dependence_only | 0 | PhysioGraph (SSM) | 3 | complete | 60 | 0.958350 (57961/60480) | null (0/0) | 0.852298 (51547/60480) | 0.891470 (50303/56427) | 0.306933 (1244/4053) | 7.121843; 4.519675; 0.317942; 0.966623; 0.148614; 0.751592 | [run](main/dependence_only/point0/physiograph/seed3/run.json) |
| dependence_only | 1 | Control-GRU | 0 | complete | 60 | 0.997718 (60342/60480) | null (0/0) | 0.894329 (54089/60480) | 0.920884 (52611/57131) | 0.441326 (1478/3349) | 6.357591; 3.438125; 0.089775; 0.503578; 0.124466; 0.737782 | [run](main/dependence_only/point1/control_gru/seed0/run.json) |
| dependence_only | 1 | Control-GRU | 1 | complete | 60 | 0.999256 (60435/60480) | null (0/0) | 0.878687 (53143/60480) | 0.904113 (51350/56796) | 0.486699 (1793/3684) | 6.976895; 4.072747; 0.131775; 0.605322; 0.130092; 0.742273 | [run](main/dependence_only/point1/control_gru/seed1/run.json) |
| dependence_only | 1 | Control-GRU | 2 | complete | 60 | 0.984342 (59533/60480) | null (0/0) | 0.892626 (53986/60480) | 0.916204 (52263/57043) | 0.501309 (1723/3437) | 7.186292; 4.122315; 0.103611; 0.578239; 0.162049; 0.847622 | [run](main/dependence_only/point1/control_gru/seed2/run.json) |
| dependence_only | 1 | Control-GRU | 3 | complete | 60 | 0.963905 (58297/60480) | null (0/0) | 0.860400 (52037/60480) | 0.882733 (49810/56427) | 0.549470 (2227/4053) | 6.672126; 3.708298; 0.119025; 0.616499; 0.133845; 0.756089 | [run](main/dependence_only/point1/control_gru/seed3/run.json) |
| dependence_only | 1 | CRN-lite | 0 | complete | 60 | 0.998049 (60362/60480) | null (0/0) | 0.890856 (53879/60480) | 0.916385 (52354/57131) | 0.455360 (1525/3349) | 6.379395; 3.437925; 0.093889; 0.515322; 0.125245; 0.736305 | [run](main/dependence_only/point1/crn_lite/seed0/run.json) |
| dependence_only | 1 | CRN-lite | 1 | complete | 60 | 0.999405 (60444/60480) | null (0/0) | 0.905655 (54774/60480) | 0.934485 (53075/56796) | 0.461183 (1699/3684) | 6.903294; 3.958162; 0.126607; 0.579407; 0.129482; 0.738490 | [run](main/dependence_only/point1/crn_lite/seed1/run.json) |
| dependence_only | 1 | CRN-lite | 2 | complete | 60 | 0.974934 (58964/60480) | null (0/0) | 0.889153 (53776/60480) | 0.912154 (52032/57043) | 0.507419 (1744/3437) | 7.196767; 4.140413; 0.103835; 0.599424; 0.163394; 0.842692 | [run](main/dependence_only/point1/crn_lite/seed2/run.json) |
| dependence_only | 1 | CRN-lite | 3 | complete | 60 | 0.968337 (58565/60480) | null (0/0) | 0.858185 (51903/60480) | 0.880412 (49679/56427) | 0.548729 (2224/4053) | 6.657797; 3.672525; 0.120549; 0.617908; 0.136253; 0.752316 | [run](main/dependence_only/point1/crn_lite/seed3/run.json) |
| dependence_only | 1 | PhysioGraph-GRU | 0 | complete | 60 | 0.964649 (58342/60480) | null (0/0) | 0.838095 (50688/60480) | 0.858606 (49053/57131) | 0.488205 (1635/3349) | 6.063597; 3.409932; 0.091810; 0.556090; 0.121553; 0.705536 | [run](main/dependence_only/point1/physiograph_gru/seed0/run.json) |
| dependence_only | 1 | PhysioGraph-GRU | 1 | complete | 60 | 0.958697 (57982/60480) | null (0/0) | 0.868204 (52509/60480) | 0.896102 (50895/56796) | 0.438111 (1614/3684) | 7.379746; 4.218513; 0.124449; 0.672317; 0.136412; 0.780684 | [run](main/dependence_only/point1/physiograph_gru/seed1/run.json) |
| dependence_only | 1 | PhysioGraph-GRU | 2 | complete | 60 | 0.967080 (58489/60480) | null (0/0) | 0.875116 (52927/60480) | 0.899076 (51286/57043) | 0.477451 (1641/3437) | 7.433736; 4.277057; 0.109139; 0.628801; 0.162828; 0.876353 | [run](main/dependence_only/point1/physiograph_gru/seed2/run.json) |
| dependence_only | 1 | PhysioGraph-GRU | 3 | complete | 60 | 0.960962 (58119/60480) | null (0/0) | 0.874752 (52905/60480) | 0.891541 (50307/56427) | 0.641007 (2598/4053) | 7.166531; 3.807230; 0.115869; 0.589836; 0.134523; 0.751033 | [run](main/dependence_only/point1/physiograph_gru/seed3/run.json) |
| dependence_only | 1 | PhysioGraph (SSM) | 0 | complete | 60 | 0.947735 (57319/60480) | null (0/0) | 0.843386 (51008/60480) | 0.857993 (49018/57131) | 0.594207 (1990/3349) | 7.407991; 5.016532; 0.355378; 1.346212; 0.134278; 0.717203 | [run](main/dependence_only/point1/physiograph/seed0/run.json) |
| dependence_only | 1 | PhysioGraph (SSM) | 1 | complete | 60 | 0.927431 (56091/60480) | null (0/0) | 0.794478 (48050/60480) | 0.810427 (46029/56796) | 0.548588 (2021/3684) | 8.286283; 5.554165; 0.347390; 1.182947; 0.144776; 0.822553 | [run](main/dependence_only/point1/physiograph/seed1/run.json) |
| dependence_only | 1 | PhysioGraph (SSM) | 2 | complete | 60 | 0.968254 (58560/60480) | null (0/0) | 0.885417 (53550/60480) | 0.907228 (51751/57043) | 0.523422 (1799/3437) | 7.599134; 4.292920; 0.153887; 0.750645; 0.167954; 0.878972 | [run](main/dependence_only/point1/physiograph/seed2/run.json) |
| dependence_only | 1 | PhysioGraph (SSM) | 3 | complete | 60 | 0.966022 (58425/60480) | null (0/0) | 0.858267 (51908/60480) | 0.895919 (50554/56427) | 0.334074 (1354/4053) | 7.795177; 5.123628; 0.330663; 1.043505; 0.152006; 0.779317 | [run](main/dependence_only/point1/physiograph/seed3/run.json) |
| dependence_only | 2 | Control-GRU | 0 | complete | 60 | 0.998743 (60404/60480) | null (0/0) | 0.891634 (53926/60480) | 0.915230 (52288/57131) | 0.489101 (1638/3349) | 6.372024; 3.440209; 0.089487; 0.505184; 0.124840; 0.736216 | [run](main/dependence_only/point2/control_gru/seed0/run.json) |
| dependence_only | 2 | Control-GRU | 1 | complete | 60 | 0.999074 (60424/60480) | null (0/0) | 0.867477 (52465/60480) | 0.885802 (50310/56796) | 0.584962 (2155/3684) | 6.942372; 4.050312; 0.132944; 0.609508; 0.130055; 0.742275 | [run](main/dependence_only/point2/control_gru/seed1/run.json) |
| dependence_only | 2 | Control-GRU | 2 | complete | 60 | 0.972421 (58812/60480) | null (0/0) | 0.879051 (53165/60480) | 0.898936 (51278/57043) | 0.549025 (1887/3437) | 7.120468; 4.076502; 0.105392; 0.578559; 0.161077; 0.841900 | [run](main/dependence_only/point2/control_gru/seed2/run.json) |
| dependence_only | 2 | Control-GRU | 3 | complete | 60 | 0.950050 (57459/60480) | null (0/0) | 0.836409 (50586/60480) | 0.855938 (48298/56427) | 0.564520 (2288/4053) | 6.737277; 3.728049; 0.120778; 0.625938; 0.135842; 0.761095 | [run](main/dependence_only/point2/control_gru/seed3/run.json) |
| dependence_only | 2 | CRN-lite | 0 | complete | 60 | 0.999041 (60422/60480) | null (0/0) | 0.888492 (53736/60480) | 0.911519 (52076/57131) | 0.495670 (1660/3349) | 6.389041; 3.441957; 0.094300; 0.513203; 0.125498; 0.733635 | [run](main/dependence_only/point2/crn_lite/seed0/run.json) |
| dependence_only | 2 | CRN-lite | 1 | complete | 60 | 0.999272 (60436/60480) | null (0/0) | 0.893651 (54048/60480) | 0.915980 (52024/56796) | 0.549403 (2024/3684) | 6.885236; 3.955788; 0.125450; 0.586671; 0.129407; 0.738459 | [run](main/dependence_only/point2/crn_lite/seed1/run.json) |
| dependence_only | 2 | CRN-lite | 2 | complete | 60 | 0.958714 (57983/60480) | null (0/0) | 0.869527 (52589/60480) | 0.890346 (50788/57043) | 0.524003 (1801/3437) | 7.053696; 4.082758; 0.104257; 0.597694; 0.161974; 0.834414 | [run](main/dependence_only/point2/crn_lite/seed2/run.json) |
| dependence_only | 2 | CRN-lite | 3 | complete | 60 | 0.955175 (57769/60480) | null (0/0) | 0.837004 (50622/60480) | 0.856452 (48327/56427) | 0.566247 (2295/4053) | 6.742823; 3.689727; 0.121627; 0.626450; 0.138878; 0.759611 | [run](main/dependence_only/point2/crn_lite/seed3/run.json) |
| dependence_only | 2 | PhysioGraph-GRU | 0 | complete | 60 | 0.973396 (58871/60480) | null (0/0) | 0.877877 (53094/60480) | 0.900352 (51438/57131) | 0.494476 (1656/3349) | 6.105776; 3.400516; 0.091380; 0.540856; 0.121541; 0.699671 | [run](main/dependence_only/point2/physiograph_gru/seed0/run.json) |
| dependence_only | 2 | PhysioGraph-GRU | 1 | complete | 60 | 0.945304 (57172/60480) | null (0/0) | 0.850546 (51441/60480) | 0.875167 (49706/56796) | 0.470955 (1735/3684) | 7.798073; 4.500032; 0.137723; 0.754398; 0.134554; 0.872685 | [run](main/dependence_only/point2/physiograph_gru/seed1/run.json) |
| dependence_only | 2 | PhysioGraph-GRU | 2 | complete | 60 | 0.957358 (57901/60480) | null (0/0) | 0.860698 (52055/60480) | 0.878390 (50106/57043) | 0.567064 (1949/3437) | 7.134823; 4.175484; 0.119915; 0.680196; 0.159455; 0.860932 | [run](main/dependence_only/point2/physiograph_gru/seed2/run.json) |
| dependence_only | 2 | PhysioGraph-GRU | 3 | complete | 60 | 0.946511 (57245/60480) | null (0/0) | 0.851802 (51517/60480) | 0.872083 (49209/56427) | 0.569455 (2308/4053) | 6.727227; 3.709421; 0.114965; 0.618556; 0.129761; 0.729505 | [run](main/dependence_only/point2/physiograph_gru/seed3/run.json) |
| dependence_only | 2 | PhysioGraph (SSM) | 0 | complete | 60 | 0.984292 (59530/60480) | null (0/0) | 0.871974 (52737/60480) | 0.896781 (51234/57131) | 0.448791 (1503/3349) | 7.035655; 4.511594; 0.334631; 1.643586; 0.135568; 0.737947 | [run](main/dependence_only/point2/physiograph/seed0/run.json) |
| dependence_only | 2 | PhysioGraph (SSM) | 1 | complete | 60 | 0.951951 (57574/60480) | null (0/0) | 0.792741 (47945/60480) | 0.809476 (45975/56796) | 0.534745 (1970/3684) | 8.164508; 4.688995; 0.357991; 1.555999; 0.139908; 0.793007 | [run](main/dependence_only/point2/physiograph/seed1/run.json) |
| dependence_only | 2 | PhysioGraph (SSM) | 2 | complete | 60 | 0.957688 (57921/60480) | null (0/0) | 0.873859 (52851/60480) | 0.894869 (51046/57043) | 0.525167 (1805/3437) | 7.272270; 4.868699; 0.181033; 1.008232; 0.160903; 0.832926 | [run](main/dependence_only/point2/physiograph/seed2/run.json) |
| dependence_only | 2 | PhysioGraph (SSM) | 3 | complete | 60 | 0.957259 (57895/60480) | null (0/0) | 0.830159 (50208/60480) | 0.870275 (49107/56427) | 0.271651 (1101/4053) | 6.880746; 4.634911; 0.317838; 1.122546; 0.134644; 0.781779 | [run](main/dependence_only/point2/physiograph/seed3/run.json) |
| dependence_only | 3 | Control-GRU | 0 | complete | 60 | 0.999537 (60452/60480) | null (0/0) | 0.881994 (53343/60480) | 0.901945 (51529/57131) | 0.541654 (1814/3349) | 6.435366; 3.462285; 0.089877; 0.509131; 0.126899; 0.735992 | [run](main/dependence_only/point3/control_gru/seed0/run.json) |
| dependence_only | 3 | Control-GRU | 1 | complete | 60 | 0.987384 (59717/60480) | null (0/0) | 0.832986 (50379/60480) | 0.843985 (47935/56796) | 0.663409 (2444/3684) | 6.959945; 4.041854; 0.135856; 0.608457; 0.131205; 0.746077 | [run](main/dependence_only/point3/control_gru/seed1/run.json) |
| dependence_only | 3 | Control-GRU | 2 | complete | 60 | 0.949769 (57442/60480) | null (0/0) | 0.848843 (51338/60480) | 0.864839 (49333/57043) | 0.583358 (2005/3437) | 7.047114; 4.052262; 0.101860; 0.578274; 0.161269; 0.839758 | [run](main/dependence_only/point3/control_gru/seed2/run.json) |
| dependence_only | 3 | Control-GRU | 3 | complete | 60 | 0.927265 (56081/60480) | null (0/0) | 0.805605 (48723/60480) | 0.822691 (46422/56427) | 0.567728 (2301/4053) | 6.809869; 3.748850; 0.121455; 0.633517; 0.137996; 0.765403 | [run](main/dependence_only/point3/control_gru/seed3/run.json) |
| dependence_only | 3 | CRN-lite | 0 | complete | 60 | 0.999719 (60463/60480) | null (0/0) | 0.878340 (53122/60480) | 0.897674 (51285/57131) | 0.548522 (1837/3349) | 6.459885; 3.469829; 0.094868; 0.515170; 0.127879; 0.733376 | [run](main/dependence_only/point3/crn_lite/seed0/run.json) |
| dependence_only | 3 | CRN-lite | 1 | complete | 60 | 0.990030 (59877/60480) | null (0/0) | 0.853687 (51631/60480) | 0.867790 (49287/56796) | 0.636265 (2344/3684) | 6.924378; 3.965609; 0.126499; 0.590181; 0.130733; 0.744150 | [run](main/dependence_only/point3/crn_lite/seed1/run.json) |
| dependence_only | 3 | CRN-lite | 2 | complete | 60 | 0.928836 (56176/60480) | null (0/0) | 0.832606 (50356/60480) | 0.851831 (48591/57043) | 0.513529 (1765/3437) | 6.950193; 4.042698; 0.102291; 0.596176; 0.161633; 0.833082 | [run](main/dependence_only/point3/crn_lite/seed2/run.json) |
| dependence_only | 3 | CRN-lite | 3 | complete | 60 | 0.938095 (56736/60480) | null (0/0) | 0.815112 (49298/60480) | 0.831712 (46931/56427) | 0.584012 (2367/4053) | 6.848223; 3.721679; 0.121178; 0.637579; 0.141755; 0.767576 | [run](main/dependence_only/point3/crn_lite/seed3/run.json) |
| dependence_only | 3 | PhysioGraph-GRU | 0 | complete | 60 | 0.988360 (59776/60480) | null (0/0) | 0.886111 (53592/60480) | 0.906916 (51813/57131) | 0.531203 (1779/3349) | 6.494557; 3.518097; 0.099379; 0.634404; 0.124357; 0.732635 | [run](main/dependence_only/point3/physiograph_gru/seed0/run.json) |
| dependence_only | 3 | PhysioGraph-GRU | 1 | complete | 60 | 0.929812 (56235/60480) | null (0/0) | 0.840592 (50839/60480) | 0.860589 (48878/56796) | 0.532302 (1961/3684) | 7.784953; 4.390455; 0.138709; 0.714860; 0.144589; 0.836314 | [run](main/dependence_only/point3/physiograph_gru/seed1/run.json) |
| dependence_only | 3 | PhysioGraph-GRU | 2 | complete | 60 | 0.936359 (56631/60480) | null (0/0) | 0.832738 (50364/60480) | 0.844942 (48198/57043) | 0.630201 (2166/3437) | 7.392333; 4.235179; 0.148973; 0.745640; 0.162197; 0.860880 | [run](main/dependence_only/point3/physiograph_gru/seed2/run.json) |
| dependence_only | 3 | PhysioGraph-GRU | 3 | complete | 60 | 0.933466 (56456/60480) | null (0/0) | 0.830341 (50219/60480) | 0.845641 (47717/56427) | 0.617321 (2502/4053) | 6.800235; 3.710542; 0.118528; 0.601238; 0.134701; 0.742885 | [run](main/dependence_only/point3/physiograph_gru/seed3/run.json) |
| dependence_only | 3 | PhysioGraph (SSM) | 0 | complete | 60 | 0.963558 (58276/60480) | null (0/0) | 0.802745 (48550/60480) | 0.805780 (46035/57131) | 0.750970 (2515/3349) | 8.407667; 4.814236; 0.369729; 2.411002; 0.160306; 0.762502 | [run](main/dependence_only/point3/physiograph/seed0/run.json) |
| dependence_only | 3 | PhysioGraph (SSM) | 1 | complete | 60 | 0.908234 (54930/60480) | null (0/0) | 0.762087 (46091/60480) | 0.771568 (43822/56796) | 0.615907 (2269/3684) | 7.571335; 4.712375; 0.334888; 1.066606; 0.137855; 0.748663 | [run](main/dependence_only/point3/physiograph/seed1/run.json) |
| dependence_only | 3 | PhysioGraph (SSM) | 2 | complete | 60 | 0.934540 (56521/60480) | null (0/0) | 0.854266 (51666/60480) | 0.872885 (49792/57043) | 0.545243 (1874/3437) | 7.393320; 4.652431; 0.147919; 0.774590; 0.160867; 0.841724 | [run](main/dependence_only/point3/physiograph/seed2/run.json) |
| dependence_only | 3 | PhysioGraph (SSM) | 3 | complete | 60 | 0.927546 (56098/60480) | null (0/0) | 0.788575 (47693/60480) | 0.817481 (46128/56427) | 0.386134 (1565/4053) | 6.919705; 4.358533; 0.329103; 1.153390; 0.142776; 0.740415 | [run](main/dependence_only/point3/physiograph/seed3/run.json) |
| dependence_only | 4 | Control-GRU | 0 | complete | 60 | 0.999223 (60433/60480) | null (0/0) | 0.847354 (51248/60480) | 0.857573 (48994/57131) | 0.673037 (2254/3349) | 6.618002; 3.527128; 0.092373; 0.518645; 0.132765; 0.743872 | [run](main/dependence_only/point4/control_gru/seed0/run.json) |
| dependence_only | 4 | Control-GRU | 1 | complete | 60 | 0.886806 (53634/60480) | null (0/0) | 0.728356 (44051/60480) | 0.728801 (41393/56796) | 0.721498 (2658/3684) | 7.003760; 4.014573; 0.138613; 0.611101; 0.133362; 0.751496 | [run](main/dependence_only/point4/control_gru/seed1/run.json) |
| dependence_only | 4 | Control-GRU | 2 | complete | 60 | 0.857771 (51878/60480) | null (0/0) | 0.725397 (43872/60480) | 0.731571 (41731/57043) | 0.622927 (2141/3437) | 7.087825; 4.089144; 0.099179; 0.575999; 0.164526; 0.844142 | [run](main/dependence_only/point4/control_gru/seed2/run.json) |
| dependence_only | 4 | Control-GRU | 3 | complete | 60 | 0.890394 (53851/60480) | null (0/0) | 0.769345 (46530/60480) | 0.782888 (44176/56427) | 0.580804 (2354/4053) | 6.939548; 3.773824; 0.123918; 0.645637; 0.142028; 0.771142 | [run](main/dependence_only/point4/control_gru/seed3/run.json) |
| dependence_only | 4 | CRN-lite | 0 | complete | 60 | 0.999653 (60459/60480) | null (0/0) | 0.845734 (51150/60480) | 0.855928 (48900/57131) | 0.671842 (2250/3349) | 6.625786; 3.533498; 0.097871; 0.519893; 0.133811; 0.739761 | [run](main/dependence_only/point4/crn_lite/seed0/run.json) |
| dependence_only | 4 | CRN-lite | 1 | complete | 60 | 0.883168 (53414/60480) | null (0/0) | 0.746561 (45152/60480) | 0.749401 (42563/56796) | 0.702769 (2589/3684) | 6.981865; 3.963775; 0.128538; 0.588915; 0.133151; 0.751820 | [run](main/dependence_only/point4/crn_lite/seed1/run.json) |
| dependence_only | 4 | CRN-lite | 2 | complete | 60 | 0.835747 (50546/60480) | null (0/0) | 0.722487 (43696/60480) | 0.734691 (41909/57043) | 0.519930 (1787/3437) | 6.915530; 3.994300; 0.101602; 0.584447; 0.163735; 0.841365 | [run](main/dependence_only/point4/crn_lite/seed2/run.json) |
| dependence_only | 4 | CRN-lite | 3 | complete | 60 | 0.918700 (55563/60480) | null (0/0) | 0.775777 (46919/60480) | 0.787105 (44414/56427) | 0.618061 (2505/4053) | 7.023730; 3.780958; 0.122903; 0.651929; 0.146248; 0.777213 | [run](main/dependence_only/point4/crn_lite/seed3/run.json) |
| dependence_only | 4 | PhysioGraph-GRU | 0 | complete | 60 | 0.948578 (57370/60480) | null (0/0) | 0.807854 (48859/60480) | 0.816982 (46675/57131) | 0.652135 (2184/3349) | 6.495083; 3.509233; 0.101602; 0.635625; 0.126611; 0.726596 | [run](main/dependence_only/point4/physiograph_gru/seed0/run.json) |
| dependence_only | 4 | PhysioGraph-GRU | 1 | complete | 60 | 0.878786 (53149/60480) | null (0/0) | 0.770982 (46629/60480) | 0.776410 (44097/56796) | 0.687296 (2532/3684) | 7.872291; 4.476235; 0.124710; 0.646420; 0.135423; 0.913186 | [run](main/dependence_only/point4/physiograph_gru/seed1/run.json) |
| dependence_only | 4 | PhysioGraph-GRU | 2 | complete | 60 | 0.853439 (51616/60480) | null (0/0) | 0.739798 (44743/60480) | 0.744807 (42486/57043) | 0.656677 (2257/3437) | 7.231737; 4.157477; 0.123298; 0.582844; 0.162102; 0.880023 | [run](main/dependence_only/point4/physiograph_gru/seed2/run.json) |
| dependence_only | 4 | PhysioGraph-GRU | 3 | complete | 60 | 0.905919 (54790/60480) | null (0/0) | 0.797189 (48214/60480) | 0.810764 (45749/56427) | 0.608191 (2465/4053) | 6.866057; 3.849924; 0.122494; 0.625464; 0.141417; 0.771342 | [run](main/dependence_only/point4/physiograph_gru/seed3/run.json) |
| dependence_only | 4 | PhysioGraph (SSM) | 0 | complete | 60 | 0.949272 (57412/60480) | null (0/0) | 0.774041 (46814/60480) | 0.777336 (44410/57131) | 0.717826 (2404/3349) | 9.979146; 4.291005; 0.427857; 1.408251; 0.172144; 0.880348 | [run](main/dependence_only/point4/physiograph/seed0/run.json) |
| dependence_only | 4 | PhysioGraph (SSM) | 1 | complete | 60 | 0.868800 (52545/60480) | null (0/0) | 0.699206 (42288/60480) | 0.695806 (39519/56796) | 0.751629 (2769/3684) | 8.183687; 5.056211; 0.357517; 1.061149; 0.140138; 0.792181 | [run](main/dependence_only/point4/physiograph/seed1/run.json) |
| dependence_only | 4 | PhysioGraph (SSM) | 2 | complete | 60 | 0.836491 (50591/60480) | null (0/0) | 0.754448 (45629/60480) | 0.770682 (43962/57043) | 0.485016 (1667/3437) | 7.496863; 4.666481; 0.128827; 0.958016; 0.166537; 0.904042 | [run](main/dependence_only/point4/physiograph/seed2/run.json) |
| dependence_only | 4 | PhysioGraph (SSM) | 3 | complete | 60 | 0.907358 (54877/60480) | null (0/0) | 0.730870 (44203/60480) | 0.749801 (42309/56427) | 0.467308 (1894/4053) | 7.326874; 4.533096; 0.337245; 0.872925; 0.156688; 0.808948 | [run](main/dependence_only/point4/physiograph/seed3/run.json) |

## CRN-lite auxiliary target: every policy/seed/split

Dose is in micrograms/(kg minute). `std` is the population standard deviation of the stored labels (the per-distribution descriptive statistic, not the across-seed sample sd). The JSON additionally preserves all seven quantiles at probabilities [0.000000,0.050000,0.250000,0.500000,0.750000,0.950000,1.000000], all ten fixed-bin counts and all bin edges for every row and split. Thus no nonconstant-label conclusion relies on rounded means alone. Original source field: `balancing_target.distribution.{all,train,test}`.

| Family | Point | Seed | Split | N | Unique | Min | Max | Mean | Std | Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| support_only | 0 | 0 | all | 400 | 265 | 0.225000 | 0.275000 | 0.250000 | 0.014542 | [run](main/support_only/point0/crn_lite/seed0/run.json) |
| support_only | 0 | 0 | train | 280 | 212 | 0.225000 | 0.275000 | 0.250388 | 0.014688 | [run](main/support_only/point0/crn_lite/seed0/run.json) |
| support_only | 0 | 0 | test | 120 | 102 | 0.225752 | 0.275000 | 0.249094 | 0.014154 | [run](main/support_only/point0/crn_lite/seed0/run.json) |
| support_only | 0 | 1 | all | 400 | 265 | 0.225000 | 0.275000 | 0.250000 | 0.014542 | [run](main/support_only/point0/crn_lite/seed1/run.json) |
| support_only | 0 | 1 | train | 280 | 211 | 0.225000 | 0.275000 | 0.249159 | 0.014413 | [run](main/support_only/point0/crn_lite/seed1/run.json) |
| support_only | 0 | 1 | test | 120 | 109 | 0.225000 | 0.275000 | 0.251961 | 0.014655 | [run](main/support_only/point0/crn_lite/seed1/run.json) |
| support_only | 0 | 2 | all | 400 | 265 | 0.225000 | 0.275000 | 0.250000 | 0.014542 | [run](main/support_only/point0/crn_lite/seed2/run.json) |
| support_only | 0 | 2 | train | 280 | 215 | 0.225000 | 0.275000 | 0.249843 | 0.014720 | [run](main/support_only/point0/crn_lite/seed2/run.json) |
| support_only | 0 | 2 | test | 120 | 113 | 0.225379 | 0.275000 | 0.250366 | 0.014113 | [run](main/support_only/point0/crn_lite/seed2/run.json) |
| support_only | 0 | 3 | all | 400 | 265 | 0.225000 | 0.275000 | 0.250000 | 0.014542 | [run](main/support_only/point0/crn_lite/seed3/run.json) |
| support_only | 0 | 3 | train | 280 | 209 | 0.225000 | 0.275000 | 0.250158 | 0.014050 | [run](main/support_only/point0/crn_lite/seed3/run.json) |
| support_only | 0 | 3 | test | 120 | 107 | 0.225000 | 0.275000 | 0.249630 | 0.015624 | [run](main/support_only/point0/crn_lite/seed3/run.json) |
| support_only | 1 | 0 | all | 400 | 265 | 0.187500 | 0.312500 | 0.250000 | 0.036356 | [run](main/support_only/point1/crn_lite/seed0/run.json) |
| support_only | 1 | 0 | train | 280 | 212 | 0.187500 | 0.312500 | 0.250971 | 0.036721 | [run](main/support_only/point1/crn_lite/seed0/run.json) |
| support_only | 1 | 0 | test | 120 | 102 | 0.189380 | 0.312500 | 0.247735 | 0.035386 | [run](main/support_only/point1/crn_lite/seed0/run.json) |
| support_only | 1 | 1 | all | 400 | 265 | 0.187500 | 0.312500 | 0.250000 | 0.036356 | [run](main/support_only/point1/crn_lite/seed1/run.json) |
| support_only | 1 | 1 | train | 280 | 211 | 0.187500 | 0.312500 | 0.247899 | 0.036032 | [run](main/support_only/point1/crn_lite/seed1/run.json) |
| support_only | 1 | 1 | test | 120 | 109 | 0.187500 | 0.312500 | 0.254903 | 0.036636 | [run](main/support_only/point1/crn_lite/seed1/run.json) |
| support_only | 1 | 2 | all | 400 | 265 | 0.187500 | 0.312500 | 0.250000 | 0.036356 | [run](main/support_only/point1/crn_lite/seed2/run.json) |
| support_only | 1 | 2 | train | 280 | 215 | 0.187500 | 0.312500 | 0.249608 | 0.036800 | [run](main/support_only/point1/crn_lite/seed2/run.json) |
| support_only | 1 | 2 | test | 120 | 113 | 0.188447 | 0.312500 | 0.250914 | 0.035282 | [run](main/support_only/point1/crn_lite/seed2/run.json) |
| support_only | 1 | 3 | all | 400 | 265 | 0.187500 | 0.312500 | 0.250000 | 0.036356 | [run](main/support_only/point1/crn_lite/seed3/run.json) |
| support_only | 1 | 3 | train | 280 | 209 | 0.187500 | 0.312500 | 0.250396 | 0.035126 | [run](main/support_only/point1/crn_lite/seed3/run.json) |
| support_only | 1 | 3 | test | 120 | 107 | 0.187500 | 0.312500 | 0.249076 | 0.039061 | [run](main/support_only/point1/crn_lite/seed3/run.json) |
| support_only | 2 | 0 | all | 400 | 265 | 0.125000 | 0.375000 | 0.250000 | 0.072712 | [run](main/support_only/point2/crn_lite/seed0/run.json) |
| support_only | 2 | 0 | train | 280 | 212 | 0.125000 | 0.375000 | 0.251941 | 0.073442 | [run](main/support_only/point2/crn_lite/seed0/run.json) |
| support_only | 2 | 0 | test | 120 | 102 | 0.128759 | 0.375000 | 0.245470 | 0.070772 | [run](main/support_only/point2/crn_lite/seed0/run.json) |
| support_only | 2 | 1 | all | 400 | 265 | 0.125000 | 0.375000 | 0.250000 | 0.072712 | [run](main/support_only/point2/crn_lite/seed1/run.json) |
| support_only | 2 | 1 | train | 280 | 211 | 0.125000 | 0.375000 | 0.245797 | 0.072063 | [run](main/support_only/point2/crn_lite/seed1/run.json) |
| support_only | 2 | 1 | test | 120 | 109 | 0.125000 | 0.375000 | 0.259806 | 0.073273 | [run](main/support_only/point2/crn_lite/seed1/run.json) |
| support_only | 2 | 2 | all | 400 | 265 | 0.125000 | 0.375000 | 0.250000 | 0.072712 | [run](main/support_only/point2/crn_lite/seed2/run.json) |
| support_only | 2 | 2 | train | 280 | 215 | 0.125000 | 0.375000 | 0.249216 | 0.073600 | [run](main/support_only/point2/crn_lite/seed2/run.json) |
| support_only | 2 | 2 | test | 120 | 113 | 0.126894 | 0.375000 | 0.251829 | 0.070564 | [run](main/support_only/point2/crn_lite/seed2/run.json) |
| support_only | 2 | 3 | all | 400 | 265 | 0.125000 | 0.375000 | 0.250000 | 0.072712 | [run](main/support_only/point2/crn_lite/seed3/run.json) |
| support_only | 2 | 3 | train | 280 | 209 | 0.125000 | 0.375000 | 0.250792 | 0.070251 | [run](main/support_only/point2/crn_lite/seed3/run.json) |
| support_only | 2 | 3 | test | 120 | 107 | 0.125000 | 0.375000 | 0.248152 | 0.078122 | [run](main/support_only/point2/crn_lite/seed3/run.json) |
| support_only | 3 | 0 | all | 400 | 265 | 0.062500 | 0.437500 | 0.250000 | 0.109068 | [run](main/support_only/point3/crn_lite/seed0/run.json) |
| support_only | 3 | 0 | train | 280 | 212 | 0.062500 | 0.437500 | 0.252912 | 0.110164 | [run](main/support_only/point3/crn_lite/seed0/run.json) |
| support_only | 3 | 0 | test | 120 | 102 | 0.068139 | 0.437500 | 0.243205 | 0.106158 | [run](main/support_only/point3/crn_lite/seed0/run.json) |
| support_only | 3 | 1 | all | 400 | 265 | 0.062500 | 0.437500 | 0.250000 | 0.109068 | [run](main/support_only/point3/crn_lite/seed1/run.json) |
| support_only | 3 | 1 | train | 280 | 211 | 0.062500 | 0.437500 | 0.243696 | 0.108095 | [run](main/support_only/point3/crn_lite/seed1/run.json) |
| support_only | 3 | 1 | test | 120 | 109 | 0.062500 | 0.437500 | 0.264710 | 0.109909 | [run](main/support_only/point3/crn_lite/seed1/run.json) |
| support_only | 3 | 2 | all | 400 | 265 | 0.062500 | 0.437500 | 0.250000 | 0.109068 | [run](main/support_only/point3/crn_lite/seed2/run.json) |
| support_only | 3 | 2 | train | 280 | 215 | 0.062500 | 0.437500 | 0.248824 | 0.110400 | [run](main/support_only/point3/crn_lite/seed2/run.json) |
| support_only | 3 | 2 | test | 120 | 113 | 0.065341 | 0.437500 | 0.252743 | 0.105846 | [run](main/support_only/point3/crn_lite/seed2/run.json) |
| support_only | 3 | 3 | all | 400 | 265 | 0.062500 | 0.437500 | 0.250000 | 0.109068 | [run](main/support_only/point3/crn_lite/seed3/run.json) |
| support_only | 3 | 3 | train | 280 | 209 | 0.062500 | 0.437500 | 0.251188 | 0.105377 | [run](main/support_only/point3/crn_lite/seed3/run.json) |
| support_only | 3 | 3 | test | 120 | 107 | 0.062500 | 0.437500 | 0.247228 | 0.117183 | [run](main/support_only/point3/crn_lite/seed3/run.json) |
| support_only | 4 | 0 | all | 400 | 265 | 0.000000 | 0.500000 | 0.250000 | 0.145424 | [run](main/support_only/point4/crn_lite/seed0/run.json) |
| support_only | 4 | 0 | train | 280 | 212 | 0.000000 | 0.500000 | 0.253883 | 0.146885 | [run](main/support_only/point4/crn_lite/seed0/run.json) |
| support_only | 4 | 0 | test | 120 | 102 | 0.007519 | 0.500000 | 0.240941 | 0.141544 | [run](main/support_only/point4/crn_lite/seed0/run.json) |
| support_only | 4 | 1 | all | 400 | 265 | 0.000000 | 0.500000 | 0.250000 | 0.145424 | [run](main/support_only/point4/crn_lite/seed1/run.json) |
| support_only | 4 | 1 | train | 280 | 211 | 0.000000 | 0.500000 | 0.241594 | 0.144126 | [run](main/support_only/point4/crn_lite/seed1/run.json) |
| support_only | 4 | 1 | test | 120 | 109 | 0.000000 | 0.500000 | 0.269613 | 0.146545 | [run](main/support_only/point4/crn_lite/seed1/run.json) |
| support_only | 4 | 2 | all | 400 | 265 | 0.000000 | 0.500000 | 0.250000 | 0.145424 | [run](main/support_only/point4/crn_lite/seed2/run.json) |
| support_only | 4 | 2 | train | 280 | 215 | 0.000000 | 0.500000 | 0.248432 | 0.147199 | [run](main/support_only/point4/crn_lite/seed2/run.json) |
| support_only | 4 | 2 | test | 120 | 113 | 0.003788 | 0.500000 | 0.253658 | 0.141128 | [run](main/support_only/point4/crn_lite/seed2/run.json) |
| support_only | 4 | 3 | all | 400 | 265 | 0.000000 | 0.500000 | 0.250000 | 0.145424 | [run](main/support_only/point4/crn_lite/seed3/run.json) |
| support_only | 4 | 3 | train | 280 | 209 | 0.000000 | 0.500000 | 0.251584 | 0.140502 | [run](main/support_only/point4/crn_lite/seed3/run.json) |
| support_only | 4 | 3 | test | 120 | 107 | 0.000000 | 0.500000 | 0.246303 | 0.156245 | [run](main/support_only/point4/crn_lite/seed3/run.json) |
| dependence_only | 0 | 0 | all | 400 | 265 | 0.000000 | 0.500000 | 0.250000 | 0.145424 | [run](main/dependence_only/point0/crn_lite/seed0/run.json) |
| dependence_only | 0 | 0 | train | 280 | 218 | 0.000000 | 0.500000 | 0.250612 | 0.145884 | [run](main/dependence_only/point0/crn_lite/seed0/run.json) |
| dependence_only | 0 | 0 | test | 120 | 109 | 0.000000 | 0.500000 | 0.248572 | 0.144335 | [run](main/dependence_only/point0/crn_lite/seed0/run.json) |
| dependence_only | 0 | 1 | all | 400 | 265 | 0.000000 | 0.500000 | 0.250000 | 0.145424 | [run](main/dependence_only/point0/crn_lite/seed1/run.json) |
| dependence_only | 0 | 1 | train | 280 | 210 | 0.000000 | 0.500000 | 0.247266 | 0.143337 | [run](main/dependence_only/point0/crn_lite/seed1/run.json) |
| dependence_only | 0 | 1 | test | 120 | 107 | 0.000000 | 0.500000 | 0.256379 | 0.149987 | [run](main/dependence_only/point0/crn_lite/seed1/run.json) |
| dependence_only | 0 | 2 | all | 400 | 265 | 0.000000 | 0.500000 | 0.250000 | 0.145424 | [run](main/dependence_only/point0/crn_lite/seed2/run.json) |
| dependence_only | 0 | 2 | train | 280 | 213 | 0.000000 | 0.500000 | 0.249835 | 0.148670 | [run](main/dependence_only/point0/crn_lite/seed2/run.json) |
| dependence_only | 0 | 2 | test | 120 | 111 | 0.000000 | 0.500000 | 0.250384 | 0.137551 | [run](main/dependence_only/point0/crn_lite/seed2/run.json) |
| dependence_only | 0 | 3 | all | 400 | 265 | 0.000000 | 0.500000 | 0.250000 | 0.145424 | [run](main/dependence_only/point0/crn_lite/seed3/run.json) |
| dependence_only | 0 | 3 | train | 280 | 210 | 0.000000 | 0.500000 | 0.248697 | 0.145558 | [run](main/dependence_only/point0/crn_lite/seed3/run.json) |
| dependence_only | 0 | 3 | test | 120 | 107 | 0.000000 | 0.500000 | 0.253041 | 0.145067 | [run](main/dependence_only/point0/crn_lite/seed3/run.json) |
| dependence_only | 1 | 0 | all | 400 | 265 | 0.000000 | 0.500000 | 0.250000 | 0.145424 | [run](main/dependence_only/point1/crn_lite/seed0/run.json) |
| dependence_only | 1 | 0 | train | 280 | 213 | 0.000000 | 0.500000 | 0.251655 | 0.145800 | [run](main/dependence_only/point1/crn_lite/seed0/run.json) |
| dependence_only | 1 | 0 | test | 120 | 102 | 0.000000 | 0.500000 | 0.246139 | 0.144471 | [run](main/dependence_only/point1/crn_lite/seed0/run.json) |
| dependence_only | 1 | 1 | all | 400 | 265 | 0.000000 | 0.500000 | 0.250000 | 0.145424 | [run](main/dependence_only/point1/crn_lite/seed1/run.json) |
| dependence_only | 1 | 1 | train | 280 | 212 | 0.000000 | 0.500000 | 0.245812 | 0.142970 | [run](main/dependence_only/point1/crn_lite/seed1/run.json) |
| dependence_only | 1 | 1 | test | 120 | 107 | 0.000000 | 0.500000 | 0.259773 | 0.150544 | [run](main/dependence_only/point1/crn_lite/seed1/run.json) |
| dependence_only | 1 | 2 | all | 400 | 265 | 0.000000 | 0.500000 | 0.250000 | 0.145424 | [run](main/dependence_only/point1/crn_lite/seed2/run.json) |
| dependence_only | 1 | 2 | train | 280 | 212 | 0.000000 | 0.500000 | 0.248822 | 0.147938 | [run](main/dependence_only/point1/crn_lite/seed2/run.json) |
| dependence_only | 1 | 2 | test | 120 | 110 | 0.000000 | 0.500000 | 0.252748 | 0.139344 | [run](main/dependence_only/point1/crn_lite/seed2/run.json) |
| dependence_only | 1 | 3 | all | 400 | 265 | 0.000000 | 0.500000 | 0.250000 | 0.145424 | [run](main/dependence_only/point1/crn_lite/seed3/run.json) |
| dependence_only | 1 | 3 | train | 280 | 214 | 0.000000 | 0.500000 | 0.248895 | 0.145017 | [run](main/dependence_only/point1/crn_lite/seed3/run.json) |
| dependence_only | 1 | 3 | test | 120 | 111 | 0.000000 | 0.500000 | 0.252578 | 0.146337 | [run](main/dependence_only/point1/crn_lite/seed3/run.json) |
| dependence_only | 2 | 0 | all | 400 | 265 | 0.000000 | 0.500000 | 0.250000 | 0.145424 | [run](main/dependence_only/point2/crn_lite/seed0/run.json) |
| dependence_only | 2 | 0 | train | 280 | 213 | 0.000000 | 0.500000 | 0.252530 | 0.146477 | [run](main/dependence_only/point2/crn_lite/seed0/run.json) |
| dependence_only | 2 | 0 | test | 120 | 103 | 0.007576 | 0.500000 | 0.244096 | 0.142763 | [run](main/dependence_only/point2/crn_lite/seed0/run.json) |
| dependence_only | 2 | 1 | all | 400 | 265 | 0.000000 | 0.500000 | 0.250000 | 0.145424 | [run](main/dependence_only/point2/crn_lite/seed1/run.json) |
| dependence_only | 2 | 1 | train | 280 | 217 | 0.003759 | 0.500000 | 0.244329 | 0.142654 | [run](main/dependence_only/point2/crn_lite/seed1/run.json) |
| dependence_only | 2 | 1 | test | 120 | 111 | 0.000000 | 0.500000 | 0.263232 | 0.150865 | [run](main/dependence_only/point2/crn_lite/seed1/run.json) |
| dependence_only | 2 | 2 | all | 400 | 265 | 0.000000 | 0.500000 | 0.250000 | 0.145424 | [run](main/dependence_only/point2/crn_lite/seed2/run.json) |
| dependence_only | 2 | 2 | train | 280 | 209 | 0.000000 | 0.500000 | 0.248310 | 0.146803 | [run](main/dependence_only/point2/crn_lite/seed2/run.json) |
| dependence_only | 2 | 2 | test | 120 | 107 | 0.000000 | 0.500000 | 0.253943 | 0.142076 | [run](main/dependence_only/point2/crn_lite/seed2/run.json) |
| dependence_only | 2 | 3 | all | 400 | 265 | 0.000000 | 0.500000 | 0.250000 | 0.145424 | [run](main/dependence_only/point2/crn_lite/seed3/run.json) |
| dependence_only | 2 | 3 | train | 280 | 212 | 0.000000 | 0.500000 | 0.249607 | 0.144610 | [run](main/dependence_only/point2/crn_lite/seed3/run.json) |
| dependence_only | 2 | 3 | test | 120 | 109 | 0.000000 | 0.500000 | 0.250916 | 0.147303 | [run](main/dependence_only/point2/crn_lite/seed3/run.json) |
| dependence_only | 3 | 0 | all | 400 | 265 | 0.000000 | 0.500000 | 0.250000 | 0.145424 | [run](main/dependence_only/point3/crn_lite/seed0/run.json) |
| dependence_only | 3 | 0 | train | 280 | 214 | 0.000000 | 0.500000 | 0.253698 | 0.146775 | [run](main/dependence_only/point3/crn_lite/seed0/run.json) |
| dependence_only | 3 | 0 | test | 120 | 104 | 0.007576 | 0.500000 | 0.241370 | 0.141849 | [run](main/dependence_only/point3/crn_lite/seed0/run.json) |
| dependence_only | 3 | 1 | all | 400 | 265 | 0.000000 | 0.500000 | 0.250000 | 0.145424 | [run](main/dependence_only/point3/crn_lite/seed1/run.json) |
| dependence_only | 3 | 1 | train | 280 | 211 | 0.000000 | 0.500000 | 0.242836 | 0.143236 | [run](main/dependence_only/point3/crn_lite/seed1/run.json) |
| dependence_only | 3 | 1 | test | 120 | 107 | 0.000000 | 0.500000 | 0.266717 | 0.149074 | [run](main/dependence_only/point3/crn_lite/seed1/run.json) |
| dependence_only | 3 | 2 | all | 400 | 265 | 0.000000 | 0.500000 | 0.250000 | 0.145424 | [run](main/dependence_only/point3/crn_lite/seed2/run.json) |
| dependence_only | 3 | 2 | train | 280 | 208 | 0.000000 | 0.500000 | 0.248028 | 0.145862 | [run](main/dependence_only/point3/crn_lite/seed2/run.json) |
| dependence_only | 3 | 2 | test | 120 | 106 | 0.000000 | 0.500000 | 0.254601 | 0.144294 | [run](main/dependence_only/point3/crn_lite/seed2/run.json) |
| dependence_only | 3 | 3 | all | 400 | 265 | 0.000000 | 0.500000 | 0.250000 | 0.145424 | [run](main/dependence_only/point3/crn_lite/seed3/run.json) |
| dependence_only | 3 | 3 | train | 280 | 215 | 0.000000 | 0.500000 | 0.249840 | 0.143113 | [run](main/dependence_only/point3/crn_lite/seed3/run.json) |
| dependence_only | 3 | 3 | test | 120 | 111 | 0.000000 | 0.500000 | 0.250374 | 0.150678 | [run](main/dependence_only/point3/crn_lite/seed3/run.json) |
| dependence_only | 4 | 0 | all | 400 | 265 | 0.000000 | 0.500000 | 0.250000 | 0.145424 | [run](main/dependence_only/point4/crn_lite/seed0/run.json) |
| dependence_only | 4 | 0 | train | 280 | 212 | 0.000000 | 0.500000 | 0.253883 | 0.146885 | [run](main/dependence_only/point4/crn_lite/seed0/run.json) |
| dependence_only | 4 | 0 | test | 120 | 102 | 0.007519 | 0.500000 | 0.240941 | 0.141544 | [run](main/dependence_only/point4/crn_lite/seed0/run.json) |
| dependence_only | 4 | 1 | all | 400 | 265 | 0.000000 | 0.500000 | 0.250000 | 0.145424 | [run](main/dependence_only/point4/crn_lite/seed1/run.json) |
| dependence_only | 4 | 1 | train | 280 | 211 | 0.000000 | 0.500000 | 0.241594 | 0.144126 | [run](main/dependence_only/point4/crn_lite/seed1/run.json) |
| dependence_only | 4 | 1 | test | 120 | 109 | 0.000000 | 0.500000 | 0.269613 | 0.146545 | [run](main/dependence_only/point4/crn_lite/seed1/run.json) |
| dependence_only | 4 | 2 | all | 400 | 265 | 0.000000 | 0.500000 | 0.250000 | 0.145424 | [run](main/dependence_only/point4/crn_lite/seed2/run.json) |
| dependence_only | 4 | 2 | train | 280 | 215 | 0.000000 | 0.500000 | 0.248432 | 0.147199 | [run](main/dependence_only/point4/crn_lite/seed2/run.json) |
| dependence_only | 4 | 2 | test | 120 | 113 | 0.003788 | 0.500000 | 0.253658 | 0.141128 | [run](main/dependence_only/point4/crn_lite/seed2/run.json) |
| dependence_only | 4 | 3 | all | 400 | 265 | 0.000000 | 0.500000 | 0.250000 | 0.145424 | [run](main/dependence_only/point4/crn_lite/seed3/run.json) |
| dependence_only | 4 | 3 | train | 280 | 209 | 0.000000 | 0.500000 | 0.251584 | 0.140502 | [run](main/dependence_only/point4/crn_lite/seed3/run.json) |
| dependence_only | 4 | 3 | test | 120 | 107 | 0.000000 | 0.500000 | 0.246303 | 0.156245 | [run](main/dependence_only/point4/crn_lite/seed3/run.json) |

## All continuous-dose CRN diagnostic runs: 24 rows

| λ | Epochs | Seed | Status | Exact post-effect | Exact zero-effect | Tolerance A | Tolerance P | Tolerance Z | RMSE vector | Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.000000 | 60 | 0 | complete | 0.778274 (47070/60480) | null (0/0) | 0.677480 (40974/60480) | 0.684059 (39081/57131) | 0.565243 (1893/3349) | 7.826947; 4.072634; 0.109819; 1.094854; 0.150753; 0.735681 | [run](crn_diagnostic/lambda0/epochs60/seed0/run.json) |
| 0.000000 | 60 | 1 | complete | 0.837748 (50667/60480) | null (0/0) | 0.770205 (46582/60480) | 0.793260 (45054/56796) | 0.414767 (1528/3684) | 7.669543; 4.342046; 0.135464; 0.842808; 0.147059; 0.900990 | [run](crn_diagnostic/lambda0/epochs60/seed1/run.json) |
| 0.000000 | 60 | 2 | complete | 0.839798 (50791/60480) | null (0/0) | 0.778208 (47066/60480) | 0.802132 (45756/57043) | 0.381146 (1310/3437) | 7.229392; 4.435331; 0.135578; 0.854173; 0.189044; 1.013696 | [run](crn_diagnostic/lambda0/epochs60/seed2/run.json) |
| 0.000000 | 60 | 3 | complete | 0.814881 (49284/60480) | null (0/0) | 0.710103 (42947/60480) | 0.731618 (41283/56427) | 0.410560 (1664/4053) | 6.775279; 3.771233; 0.119562; 0.617353; 0.142069; 0.813055 | [run](crn_diagnostic/lambda0/epochs60/seed3/run.json) |
| 0.000000 | 120 | 0 | complete | 0.867791 (52484/60480) | null (0/0) | 0.793816 (48010/60480) | 0.812851 (46439/57131) | 0.469095 (1571/3349) | 6.329607; 3.937370; 0.158350; 0.835571; 0.132930; 0.805935 | [run](crn_diagnostic/lambda0/epochs120/seed0/run.json) |
| 0.000000 | 120 | 1 | complete | 0.871693 (52720/60480) | null (0/0) | 0.782755 (47341/60480) | 0.798912 (45375/56796) | 0.533659 (1966/3684) | 7.011299; 3.931506; 0.204646; 0.921196; 0.140265; 0.801743 | [run](crn_diagnostic/lambda0/epochs120/seed1/run.json) |
| 0.000000 | 120 | 2 | complete | 0.838062 (50686/60480) | null (0/0) | 0.757391 (45807/60480) | 0.778395 (44402/57043) | 0.408787 (1405/3437) | 8.539018; 5.662930; 0.339265; 1.126324; 0.202985; 1.029434 | [run](crn_diagnostic/lambda0/epochs120/seed2/run.json) |
| 0.000000 | 120 | 3 | complete | 0.896875 (54243/60480) | null (0/0) | 0.830357 (50220/60480) | 0.868325 (48997/56427) | 0.301752 (1223/4053) | 7.359988; 4.720498; 0.201669; 1.109294; 0.154594; 0.925262 | [run](crn_diagnostic/lambda0/epochs120/seed3/run.json) |
| 0.250000 | 60 | 0 | complete | 0.817014 (49413/60480) | null (0/0) | 0.764071 (46211/60480) | 0.793440 (45330/57131) | 0.263064 (881/3349) | 7.338441; 4.565312; 0.206569; 1.211242; 0.143892; 0.877271 | [run](crn_diagnostic/lambda0.25/epochs60/seed0/run.json) |
| 0.250000 | 60 | 1 | complete | 0.860665 (52053/60480) | null (0/0) | 0.781729 (47279/60480) | 0.814441 (46257/56796) | 0.277416 (1022/3684) | 7.970975; 5.904402; 0.279216; 1.253133; 0.151017; 1.000125 | [run](crn_diagnostic/lambda0.25/epochs60/seed1/run.json) |
| 0.250000 | 60 | 2 | complete | 0.763079 (46151/60480) | null (0/0) | 0.676736 (40929/60480) | 0.701576 (40020/57043) | 0.264475 (909/3437) | 9.695151; 4.426406; 0.270658; 1.282218; 0.209866; 1.095012 | [run](crn_diagnostic/lambda0.25/epochs60/seed2/run.json) |
| 0.250000 | 60 | 3 | complete | 0.843899 (51039/60480) | null (0/0) | 0.771015 (46631/60480) | 0.811190 (45773/56427) | 0.211695 (858/4053) | 7.586775; 4.969803; 0.178230; 1.290641; 0.155713; 0.955041 | [run](crn_diagnostic/lambda0.25/epochs60/seed3/run.json) |
| 0.250000 | 120 | 0 | complete | 0.867626 (52474/60480) | null (0/0) | 0.803423 (48591/60480) | 0.839317 (47951/57131) | 0.191102 (640/3349) | 7.559913; 4.994009; 0.327815; 1.184363; 0.152724; 0.798280 | [run](crn_diagnostic/lambda0.25/epochs120/seed0/run.json) |
| 0.250000 | 120 | 1 | complete | 0.829018 (50139/60480) | null (0/0) | 0.749702 (45342/60480) | 0.778822 (44234/56796) | 0.300760 (1108/3684) | 8.948834; 6.352455; 0.323419; 1.708182; 0.155222; 0.952657 | [run](crn_diagnostic/lambda0.25/epochs120/seed1/run.json) |
| 0.250000 | 120 | 2 | complete | 0.773694 (46793/60480) | null (0/0) | 0.686938 (41546/60480) | 0.700997 (39987/57043) | 0.453593 (1559/3437) | 10.239299; 5.914391; 0.565437; 1.258967; 0.239297; 1.195420 | [run](crn_diagnostic/lambda0.25/epochs120/seed2/run.json) |
| 0.250000 | 120 | 3 | complete | 0.839104 (50749/60480) | null (0/0) | 0.760251 (45980/60480) | 0.793716 (44787/56427) | 0.294350 (1193/4053) | 9.002391; 4.694210; 0.264391; 1.353255; 0.155317; 0.944800 | [run](crn_diagnostic/lambda0.25/epochs120/seed3/run.json) |
| 1.000000 | 60 | 0 | complete | 0.765327 (46287/60480) | null (0/0) | 0.659011 (39857/60480) | 0.677706 (38718/57131) | 0.340102 (1139/3349) | 9.902176; 6.641722; 0.565665; 3.160612; 0.223281; 1.351528 | [run](crn_diagnostic/lambda1/epochs60/seed0/run.json) |
| 1.000000 | 60 | 1 | complete | 0.778274 (47070/60480) | null (0/0) | 0.697007 (42155/60480) | 0.722639 (41043/56796) | 0.301846 (1112/3684) | 9.037588; 5.169889; 0.390046; 2.531667; 0.172591; 1.134120 | [run](crn_diagnostic/lambda1/epochs60/seed1/run.json) |
| 1.000000 | 60 | 2 | complete | 0.759358 (45926/60480) | null (0/0) | 0.662765 (40084/60480) | 0.683484 (38988/57043) | 0.318883 (1096/3437) | 10.298747; 5.871680; 0.475740; 3.055090; 0.218870; 1.027100 | [run](crn_diagnostic/lambda1/epochs60/seed2/run.json) |
| 1.000000 | 60 | 3 | complete | 0.844841 (51096/60480) | null (0/0) | 0.776852 (46984/60480) | 0.814663 (45969/56427) | 0.250432 (1015/4053) | 7.927559; 6.170457; 0.356010; 1.314484; 0.162569; 1.033283 | [run](crn_diagnostic/lambda1/epochs60/seed3/run.json) |
| 1.000000 | 120 | 0 | complete | 0.782722 (47339/60480) | null (0/0) | 0.701240 (42411/60480) | 0.724055 (41366/57131) | 0.312033 (1045/3349) | 9.527777; 7.892161; 0.528204; 1.927688; 0.189126; 1.122737 | [run](crn_diagnostic/lambda1/epochs120/seed0/run.json) |
| 1.000000 | 120 | 1 | complete | 0.768254 (46464/60480) | null (0/0) | 0.685648 (41468/60480) | 0.710050 (40328/56796) | 0.309446 (1140/3684) | 7.665753; 6.172037; 0.612701; 2.139321; 0.158177; 0.870380 | [run](crn_diagnostic/lambda1/epochs120/seed1/run.json) |
| 1.000000 | 120 | 2 | complete | 0.672966 (40701/60480) | null (0/0) | 0.597057 (36110/60480) | 0.604789 (34499/57043) | 0.468723 (1611/3437) | 10.519678; 8.082043; 0.772296; 2.023163; 0.234977; 1.163567 | [run](crn_diagnostic/lambda1/epochs120/seed2/run.json) |
| 1.000000 | 120 | 3 | complete | 0.731994 (44271/60480) | null (0/0) | 0.589550 (35656/60480) | 0.603665 (34063/56427) | 0.393042 (1593/4053) | 11.729220; 9.452455; 0.524982; 2.060096; 0.199095; 1.079352 | [run](crn_diagnostic/lambda1/epochs120/seed3/run.json) |

## Provenance discrepancies and remaining evidence

Paired estimates use the specified common model/split seeds and equal recorded design metadata. Three dataset paths have multiple recorded archive hashes, affecting four run records versus current manifests; exact historical input-array identity remains unverified for those records. Intervals are computed and exposed with this qualification, not treated as a clean provenance PASS.

Dataset `experiments/counterfactual_onset_matched/artifacts/datasets/16c279d0f5dd9065e2db.npz`: current SHA256 `b89e7f71b5e31177983c17bcb2353cd8a3fd767faa22f7ca32e561455905f0e4`. Differing recorded run hashes:

- `artifacts/host/main/support_only/point2/physiograph_gru/seed0/run.json`, recorded dataset SHA256 `04641ccc94aab403639a24ab6ec043bda767d9d6a0955876bec449fd5c69bbf9`.

Dataset `experiments/counterfactual_onset_matched/artifacts/datasets/18c6c14bdd7f8b47dd73.npz`: current SHA256 `3c087f996880b3227a3facdc56141c8173d81953cddcb08db852570f75d8012f`. Differing recorded run hashes:

- `artifacts/host/main/support_only/point1/crn_lite/seed3/run.json`, recorded dataset SHA256 `7cf76268ca9faaad032c8caaf57bc8992efde4403f469ef110039459951e5915`.
- `artifacts/host/main/support_only/point1/physiograph/seed1/run.json`, recorded dataset SHA256 `7cf76268ca9faaad032c8caaf57bc8992efde4403f469ef110039459951e5915`.

Dataset `experiments/counterfactual_onset_matched/artifacts/datasets/e70bf6f71307c2baf727.npz`: current SHA256 `09e76adecca567e8ab7b15e87f46ea45d552248cd2ddc5815c847dfc0cb5e050`. Differing recorded run hashes:

- `artifacts/host/main/dependence_only/point4/crn_lite/seed3/run.json`, recorded dataset SHA256 `5ada696d43ce59d54c30bdca7cb999cc254bdd1b675ee497021ad0c2fa716324`.

Recorded source-code hashes match the current referenced files. Current dataset archives match their current manifests, and all recorded dataset metadata match those manifests. Earlier differing archive versions are unavailable in this evidence, so matching historical arrays cannot be established. The report does not assume an archive timestamp explanation. The same-seed model contrasts involving the listed records retain this qualification; no experiment or archive was rewritten. Required independent scientific assessment remains with the project lead's process.

To complete the requested randomized-dose model comparison, provide existing Control-GRU seed0–3 records on the identical onset-matched legacy (c,σ)=(0.000000,0.000000) dataset and splits, with an appropriate matched training budget. The current 184-row package remains useful and complete as a reading of its supplied evidence; it explicitly leaves that unavailable contrast null.
