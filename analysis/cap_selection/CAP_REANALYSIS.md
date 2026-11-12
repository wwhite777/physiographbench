# historical-experiment cap reanalysis — existing records, D-016 / N1

The specified validation rule selects **shared none: 105 epochs; shared admissible: 70 epochs; GRU-D: 35 epochs**. These are the family-specific caps to carry into N2 if the maintainer applies D-016. No new fits, checkpoint inference or input changes were performed.

The complete machine-readable evidence is in `cap_reanalysis.json`; `cap_reanalysis.py` regenerates both that file and this report. Markdown displays nine significant digits. JSON retains binary64 values without display rounding. Every raw observation supplies an repository-relative source location and JSON pointer; derived entries link their observations or run/contrast IDs. The source catalog supplies SHA-256 hashes. All four task-card hash prefixes match.

## Definitions and interpretation

Root mean squared error (RMSE) is the pooled masked error over observed target entries over the 12-hour forecast, in A-training standard-deviation units. Each mean averages the four saved per-seed RMSEs. A is the internal test holdout; B is the external holdout; A-validation alone selects the cap. Seeds pair by index 0–3 on exactly the same saved clinical splits. Differences are arm minus reference, or later cap minus earlier cap, so negative is better.

The paired sample standard deviation (SD) uses divisor n−1. The 95% confidence interval (CI) is mean difference ± t(0.975,3) × paired SD / √4. These are pointwise, unadjusted seed intervals, conditional on the fixed cohorts and the selected caps; they do not quantify patient/hospital sampling uncertainty or account for cap-selection uncertainty. They rely on independent, normally distributed seed differences.

Minimum detectable difference (MDD) is the effect magnitude giving 80% power in a two-sided α=0.05 paired t test under the plug-in observed paired SD. It is obtained by noncentral-t inversion, as specified in the pinned historical-experiment method. It is an uncertain planning sensitivity estimate, not observed power, an equivalence margin or proof that a null effect is absent.

**Historical validation schema:** the four 35-epoch GRU-D records have no `A_validation` block. Their scalar `validation_RMSE` is the saved A-validation pooled masked RMSE: the v4 protocol takes `metrics(val_errors)["pooled_masked_RMSE"]` from the validation loader and stores the selected `best_val` in that field. The JSON records this exact source pointer and the protocol definition; it does not invent a missing nested field. All 32 newer main records have the nested field and an exactly matching scalar.

**Stopping:** an early stop here means completed epochs strictly below the cap, with complete status and exhausted patience. A best checkpoint before the cap alone is insufficient. Main embedded curves are replayed against patience/minimum improvement; the historical records are checked using completed, best and patience fields. A run can exhaust patience exactly at its cap; that is separately counted and is not a stop before the cap.

## Family means and completion

All epoch lists follow seed order 0, 1, 2, 3. Early stops and reached-cap counts have denominator four.

| Family | Cap | A mean ± sample SD | B mean ± sample SD | A-validation mean ± sample SD | Completed epochs | Best epochs | Stops before cap | Reached cap |
|---|---:|---|---|---|---|---|---:|---:|
| Shared none | 35 | 0.755928958 ± 0.00161322692 | 0.808816976 ± 0.00192778959 | 0.767681468 ± 0.00179132759 | 35, 35, 35, 35 | 35, 34, 34, 34 | 0/4 | 4/4 |
| Shared none | 70 | 0.749557356 ± 0.0024432396 | 0.806965351 ± 0.00147189825 | 0.759080603 ± 0.00185268717 | 64, 70, 70, 70 | 56, 64, 64, 67 | 1/4 | 3/4 |
| Shared none | 105 | 0.755779081 ± 0.00142403295 | 0.812510696 ± 0.0036629392 | 0.758876829 ± 0.00149467215 | 89, 63, 85, 68 | 81, 55, 77, 60 | 4/4 | 0/4 |
| Shared admissible | 35 | 0.755070243 ± 0.00269165553 | 0.809268073 ± 0.00162409886 | 0.766740739 ± 0.00317938441 | 35, 35, 35, 35 | 35, 34, 34, 34 | 0/4 | 4/4 |
| Shared admissible | 70 | 0.757671449 ± 0.00237625569 | 0.814906538 ± 0.000701382395 | 0.764875685 ± 0.00234393298 | 64, 49, 59, 56 | 56, 41, 51, 48 | 4/4 | 0/4 |
| Shared admissible | 105 | 0.761171387 ± 0.00153277362 | 0.819490912 ± 0.00249310369 | 0.768334922 ± 0.00140330405 | 56, 51, 50, 52 | 48, 43, 42, 44 | 4/4 | 0/4 |
| GRU-D | 35 | 0.745810642 ± 0.000488972168 | 0.805874366 ± 0.000885531217 | 0.752373749 ± 0.00101331507 | 35, 35, 35, 35 | 33, 32, 31, 33 | 0/4 | 4/4 |
| GRU-D | 70 | 0.748893171 ± 0.00112143445 | 0.809563118 ± 0.00309730746 | 0.754697761 ± 0.00066640313 | 34, 30, 35, 38 | 26, 22, 27, 30 | 4/4 | 0/4 |
| GRU-D | 105 | 0.749138219 ± 0.000863740118 | 0.806866916 ± 0.00290643219 | 0.755691643 ± 0.00107682534 | 22, 30, 32, 26 | 14, 22, 24, 18 | 4/4 | 0/4 |

## Validation-only cap selection

| Family | Mean validation @35 | @70 | @105 | Selected cap | Runner-up minus selected validation |
|---|---:|---:|---:|---:|---:|
| Shared none | 0.767681468 | 0.759080603 | 0.758876829 | 105 | 0.000203773767 |
| Shared admissible | 0.766740739 | 0.764875685 | 0.768334922 | 70 | 0.0018650533 |
| GRU-D | 0.752373749 | 0.754697761 | 0.755691643 | 35 | 0.00232401152 |

Ranking uses the unrounded mean and an exact tie → smaller-cap rule. No tolerance is added, and the early-stopping minimum-improvement threshold is not reused as a cap-selection threshold. No family has an exact tie. Shared none therefore selects 105 even though its A/B test means are worse than at 70. Shared admissible selects 70 even though its A/B test means are worse than at 35. The rule is supplied by D-016; these records and their test outcomes already existed, so this reanalysis does not establish prospective blinding or erase earlier result exposure.

## Contrasts at each family’s selected cap

| ID | Contrast | Cohort/metric | Mean difference | Paired SD | 95% paired t CI | Signs −/0/+ | MDD, n=4 |
|---|---|---|---:|---:|---|---|---:|
| C046 | admissible@70 minus none@105 | A | +0.0018923676 | 0.00310235247 | [-0.00304416748, +0.00682890268] | 1/0/3 | 0.00660164891 |
| C047 | admissible@70 minus none@105 | B | +0.00239584171 | 0.00380293433 | [-0.00365547544, +0.00844715886] | 1/0/3 | 0.0080924516 |
| C048 | none@105 minus grud@35 | A | +0.00996843957 | 0.00166147748 | [+0.00732465814, +0.012612221] | 0/0/4 | 0.0035355399 |
| C049 | none@105 minus grud@35 | B | +0.00663633031 | 0.00372218563 | [+0.000713502353, +0.0125591583] | 0/0/4 | 0.00792062248 |
| C050 | admissible@70 minus grud@35 | A | +0.0118608072 | 0.00206849267 | [+0.00856937375, +0.0151522406] | 0/0/4 | 0.00440164761 |
| C051 | admissible@70 minus grud@35 | B | +0.00903217202 | 0.00113881364 | [+0.00722006539, +0.0108442787] | 0/0/4 | 0.00242333774 |

These compare admissible@70 with none@105 and both with GRU-D@35. They estimate the differences between the validation-selected family procedures, with topology, cap and schedule differences combined. Use the common-cap tables below to assess topology at matched caps. An interval containing zero does not establish equivalence.

## Admissible minus none at each common cap

| ID | Contrast | Cohort/metric | Mean difference | Paired SD | 95% paired t CI | Signs −/0/+ | MDD, n=4 |
|---|---|---|---:|---:|---|---|---:|
| C001 | admissible@35 minus none@35 | A | -0.000858715364 | 0.003376327 | [-0.00623120506, +0.00451377433] | 2/0/2 | 0.00718465283 |
| C002 | admissible@35 minus none@35 | B | +0.000451097478 | 0.00294484858 | [-0.00423481377, +0.00513700872] | 2/0/2 | 0.00626648861 |
| C003 | admissible@70 minus none@70 | A | +0.00811409257 | 0.00461401129 | [+0.000772170974, +0.0154560142] | 0/0/4 | 0.0098183823 |
| C004 | admissible@70 minus none@70 | B | +0.00794118682 | 0.0017373119 | [+0.0051767359, +0.0107056377] | 0/0/4 | 0.00369691172 |
| C005 | admissible@105 minus none@105 | A | +0.00539230576 | 0.00271581795 | [+0.00107083335, +0.00971377816] | 0/0/4 | 0.00577912303 |
| C006 | admissible@105 minus none@105 | B | +0.00698021573 | 0.00367139762 | [+0.00113820283, +0.0128222286] | 0/0/4 | 0.00781254816 |

## Within-family cap changes

A-validation changes are included alongside A/B changes so the cap decision can be inspected. Every contrast uses the same seed indices at the two caps.

| ID | Contrast | Cohort/metric | Mean difference | Paired SD | 95% paired t CI | Signs −/0/+ | MDD, n=4 |
|---|---|---|---:|---:|---|---|---:|
| C007 | none@70 minus none@35 | A | -0.00637160224 | 0.00221016957 | [-0.00988847523, -0.00285472925] | 4/0/0 | 0.00470312888 |
| C008 | none@70 minus none@35 | B | -0.00185162456 | 0.00120126411 | [-0.00376310383, +5.98547046e-05] | 4/0/0 | 0.00255622917 |
| C009 | none@70 minus none@35 | A_validation | -0.00860086434 | 0.00100543311 | [-0.0102007328, -0.0070009959] | 4/0/0 | 0.00213951073 |
| C010 | none@105 minus none@70 | A | +0.00622172497 | 0.00223067252 | [+0.0026722272, +0.00977122273] | 0/0/4 | 0.00474675813 |
| C011 | none@105 minus none@70 | B | +0.00554534511 | 0.00219986912 | [+0.00204486244, +0.00904582778] | 0/0/4 | 0.00468121004 |
| C012 | none@105 minus none@70 | A_validation | -0.000203773767 | 0.00266328009 | [-0.0044416467, +0.00403409917] | 2/0/2 | 0.00566732511 |
| C013 | none@105 minus none@35 | A | -0.000149877271 | 0.00115022944 | [-0.00198014898, +0.00168039444] | 2/0/2 | 0.00244762998 |
| C014 | none@105 minus none@35 | B | +0.00369372055 | 0.00232727489 | [-9.49313346e-06, +0.00739693423] | 0/0/4 | 0.00495232307 |
| C015 | none@105 minus none@35 | A_validation | -0.00880463811 | 0.00243351541 | [-0.0126769042, -0.00493237204] | 4/0/0 | 0.00517839752 |
| C016 | admissible@70 minus admissible@35 | A | +0.00260120569 | 0.00369250461 | [-0.00327439314, +0.00847680452] | 1/0/3 | 0.00785746276 |
| C017 | admissible@70 minus admissible@35 | B | +0.00563846478 | 0.00202108863 | [+0.00242246175, +0.00885446781] | 0/0/4 | 0.00430077423 |
| C018 | admissible@70 minus admissible@35 | A_validation | -0.0018650533 | 0.00353711978 | [-0.00749340018, +0.00376329359] | 3/0/1 | 0.00752681171 |
| C019 | admissible@105 minus admissible@70 | A | +0.00349993816 | 0.00332796949 | [-0.00179560395, +0.00879548027] | 1/0/3 | 0.0070817505 |
| C020 | admissible@105 minus admissible@70 | B | +0.00458437402 | 0.00317927275 | [-0.00047455839, +0.00964330643] | 0/0/4 | 0.00676533136 |
| C021 | admissible@105 minus admissible@70 | A_validation | +0.00345923692 | 0.00360491117 | [-0.0022769812, +0.00919545504] | 1/0/3 | 0.00767106836 |
| C022 | admissible@105 minus admissible@35 | A | +0.00610114385 | 0.00221080392 | [+0.00258326147, +0.00961902623] | 0/0/4 | 0.00470447875 |
| C023 | admissible@105 minus admissible@35 | B | +0.0102228388 | 0.00230794813 | [+0.0065503783, +0.0138952993] | 0/0/4 | 0.00491119671 |
| C024 | admissible@105 minus admissible@35 | A_validation | +0.00159418363 | 0.00316678234 | [-0.00344487376, +0.00663324101] | 1/0/3 | 0.00673875241 |
| C025 | grud@70 minus grud@35 | A | +0.00308252945 | 0.0012887802 | [+0.00103179255, +0.00513326635] | 0/0/4 | 0.00274245899 |
| C026 | grud@70 minus grud@35 | B | +0.00368875177 | 0.00236298478 | [-7.12843169e-05, +0.00744878785] | 0/0/4 | 0.0050283119 |
| C027 | grud@70 minus grud@35 | A_validation | +0.00232401152 | 0.000559975693 | [+0.00143296523, +0.00321505781] | 0/0/4 | 0.00119159991 |
| C028 | grud@105 minus grud@70 | A | +0.000245047948 | 0.000584700511 | [-0.000685341042, +0.00117543694] | 1/0/3 | 0.00124421307 |
| C029 | grud@105 minus grud@70 | B | -0.00269620147 | 0.00326998606 | [-0.00789947899, +0.00250707605] | 3/0/1 | 0.00695836468 |
| C030 | grud@105 minus grud@70 | A_validation | +0.000993881557 | 0.000964422415 | [-0.000540729719, +0.00252849283] | 0/0/4 | 0.00205224204 |
| C031 | grud@105 minus grud@35 | A | +0.0033275774 | 0.000965834135 | [+0.00179071976, +0.00486443503] | 0/0/4 | 0.00205524611 |
| C032 | grud@105 minus grud@35 | B | +0.000992550302 | 0.00310659036 | [-0.0039507282, +0.00593582881] | 2/0/2 | 0.00661066691 |
| C033 | grud@105 minus grud@35 | A_validation | +0.00331789308 | 0.000620905146 | [+0.00232989443, +0.00430589172] | 0/0/4 | 0.0013212547 |

## Organ families minus GRU-D at each common cap

| ID | Contrast | Cohort/metric | Mean difference | Paired SD | 95% paired t CI | Signs −/0/+ | MDD, n=4 |
|---|---|---|---:|---:|---|---|---:|
| C034 | none@35 minus grud@35 | A | +0.0101183168 | 0.00180301159 | [+0.00724932305, +0.0129873106] | 0/0/4 | 0.00383671733 |
| C035 | none@35 minus grud@35 | B | +0.00294260977 | 0.00165918897 | [+0.000302469864, +0.00558274967] | 0/0/4 | 0.00353067008 |
| C036 | admissible@35 minus grud@35 | A | +0.00925960148 | 0.00250152967 | [+0.00527910955, +0.0132400934] | 0/0/4 | 0.00532312841 |
| C037 | admissible@35 minus grud@35 | B | +0.00339370724 | 0.00243795211 | [-0.000485618607, +0.00727303309] | 0/0/4 | 0.0051878386 |
| C038 | none@70 minus grud@70 | A | +0.000664185153 | 0.00232347704 | [-0.00303298531, +0.00436135562] | 2/0/2 | 0.00494424145 |
| C039 | none@70 minus grud@70 | B | -0.00259776656 | 0.00392196752 | [-0.00883849208, +0.00364295895] | 3/0/1 | 0.0083457482 |
| C040 | admissible@70 minus grud@70 | A | +0.00877827772 | 0.00308608987 | [+0.00386762007, +0.0136889354] | 0/0/4 | 0.00656704291 |
| C041 | admissible@70 minus grud@70 | B | +0.00534342026 | 0.00294317672 | [+0.000660169317, +0.0100266712] | 0/0/4 | 0.00626293097 |
| C042 | none@105 minus grud@105 | A | +0.00664086217 | 0.00126624139 | [+0.00462598955, +0.0086557348] | 0/0/4 | 0.00269449754 |
| C043 | none@105 minus grud@105 | B | +0.00564378001 | 0.00634573021 | [-0.00445369281, +0.0157412528] | 1/0/3 | 0.0135033924 |
| C044 | admissible@105 minus grud@105 | A | +0.0120331679 | 0.00194786451 | [+0.00893368083, +0.015132655] | 0/0/4 | 0.004144957 |
| C045 | admissible@105 minus grud@105 | B | +0.0126239957 | 0.00507319827 | [+0.0045514052, +0.0206965863] | 0/0/4 | 0.0107955089 |

## Other Table 1 models: selected-run stopping at 35

These are the four selected runs for each model, rather than counts across its tuning grid. GRU-D is repeated as a reference. The two learned graph adapters are run at paper settings; their records are located by the pinned `paired_stats.py` Table 1 source mapping. Only their saved training metadata are used here. Their histories have zero-based epoch labels; the completed count is history length, and best epochs below are converted to one-based labels.

| Model | Selected setting | Completed epochs | Best epochs | Stops before 35 | Reached 35 | Patience exhausted exactly at 35 | Reached cap before patience |
|---|---|---|---|---:|---:|---:|---:|
| GRU | lr=0.001, large | 35, 35, 35, 35 | 33, 32, 34, 31 | 0/4 | 4/4 | 0/4 | 4/4 |
| GRU-med | lr=0.0005, large | 35, 35, 35, 35 | 33, 32, 34, 34 | 0/4 | 4/4 | 0/4 | 4/4 |
| GRU-large | lr=0.002, large | 22, 25, 28, 24 | 14, 17, 20, 16 | 4/4 | 0/4 | 0/4 | 0/4 |
| GRU-D | lr=0.0005, large | 35, 35, 35, 35 | 33, 32, 31, 33 | 0/4 | 4/4 | 0/4 | 4/4 |
| Neural CDE | lr=0.002, small | 28, 29, 24, 25 | 20, 21, 16, 17 | 4/4 | 0/4 | 0/4 | 0/4 |
| ODE-RNN | lr=0.002, small | 33, 35, 35, 33 | 25, 28, 29, 25 | 2/4 | 2/4 | 0/4 | 2/4 |
| GraphGRU | lr=0.0005, large | 27, 27, 29, 24 | 19, 19, 21, 16 | 4/4 | 0/4 | 0/4 | 0/4 |
| PhysioGraph-SSM, partitioned | lr=0.001, small | 35, 35, 35, 35 | 33, 34, 34, 35 | 0/4 | 4/4 | 0/4 | 4/4 |
| PhysioGraph-GRU, partitioned | lr=0.0005, large | 35, 35, 35, 35 | 35, 34, 35, 35 | 0/4 | 4/4 | 0/4 | 4/4 |
| t-PatchGNN | Paper settings | 35, 35, 35, 35 | 33, 34, 32, 29 | 0/4 | 4/4 | 0/4 | 4/4 |
| GraFITi | Paper settings | 35, 35, 35, 35 | 27, 29, 29, 31 | 0/4 | 4/4 | 1/4 | 3/4 |
| Persistence | No fit | NA | NA | NA | NA | NA | NA |

The 35-epoch cap can limit the selected GRU, GRU-med, GRU-D, partitioned PhysioGraph-GRU/SSM and both learned adapters; these have runs reaching the cap before patience expires. ODE-RNN is mixed across seeds. Selected GraphGRU, GRU-large and Neural CDE runs all stop before 35. Reaching a cap before patience is exhausted identifies where the available budget may bind; it does not prove that a longer cap improves validation or test error. GraFITi seed 0 exhausts patience exactly on completed epoch 35, so its other three seeds, rather than all four, reach the cap before patience. Neural CDE’s external-score replay remains unresolved; this stopping audit makes no new external ranking claim.

## Ten-pair MDD planning

Noncentral-t multipliers are 2.12794934 × observed paired SD for n=4 and 0.996001371 × observed paired SD for n=10. The primary estimate uses admissible@70 minus none@105, each at its own selected cap. Because there is no single shared selected cap, the common-cap estimates are also supplied explicitly. Ten means ten total seed pairs; retaining the original four would require six additional pairs. The selected-cap n=10 SD estimate comes from four existing cross-cap pairs and is not independently estimated from ten runs.

| Contrast ID | Contrast | Metric | Planning role | Observed paired SD (4 pairs) | MDD (10 total pairs) |
|---|---|---|---|---:|---:|
| C001 | admissible@35 minus none@35 | A | Common-cap sensitivity | 0.003376327 | 0.00336282633 |
| C002 | admissible@35 minus none@35 | B | Common-cap sensitivity | 0.00294484858 | 0.00293307323 |
| C003 | admissible@70 minus none@70 | A | Common-cap sensitivity | 0.00461401129 | 0.00459556157 |
| C004 | admissible@70 minus none@70 | B | Common-cap sensitivity | 0.0017373119 | 0.00173036504 |
| C005 | admissible@105 minus none@105 | A | Common-cap sensitivity | 0.00271581795 | 0.00270495841 |
| C006 | admissible@105 minus none@105 | B | Common-cap sensitivity | 0.00367139762 | 0.00365671707 |
| C046 | admissible@70 minus none@105 | A | Primary: each selected cap | 0.00310235247 | 0.00308994732 |
| C047 | admissible@70 minus none@105 | B | Primary: each selected cap | 0.00380293433 | 0.0037877278 |

## Plain-language reading

The lowest validation error does not identify the lowest test error in these records. In particular, the selected no-edge cap is 105, despite better A/B test means at 70. Replacing the specified choice with 70 after looking at A/B would change the selection rule. For admissible, validation chooses 70 while the 35-epoch A/B scores are better. The 35-epoch GRU-D reference has the best validation mean among its three caps.

At each family’s selected cap, the no-edge and admissible organ models both have higher mean A and B errors than GRU-D@35. Their pointwise paired intervals versus GRU-D exclude zero in the positive direction. Admissible@70 minus none@105 has positive mean differences of +0.00189237 A and +0.00239584 B, with both paired intervals containing zero and signs 1/0/3 on each cohort. These selected-procedure comparisons cannot isolate a physiological-edge effect because the caps differ. The common-cap comparisons show that the admissible-minus-none ordering depends on the cap. Neither the four-seed evidence nor the MDD calculation establishes equivalence or generalization to new hospitals.

All longer-cap runs are fresh fits with cosine period equal to the cap. A larger cap also changes early stopping and the learning-rate trajectory, so the observed changes cannot be attributed only to additional training epochs. The selected-run stopping audit also shows why a blanket statement that every baseline converged before 35 is unsupported.

## Reproduction and handoff

Run `python3 cap_reanalysis.py` in this workspace to regenerate the JSON and Markdown. Run `python3 cap_reanalysis.py --check` for an in-memory, byte-for-byte reproduction check with all pinned hashes and source fields rechecked. Python/NumPy/SciPy versions and full source hashes are recorded in the JSON. The six-cell shared configuration grid is audited separately by validation only; its seed-0 winner duplicates none@35 seed 0 and is never counted as a fifth replicate.

This data-free reconstruction checks the distributed records and numerical summaries; it does not replay omitted predictions or checkpoints.
