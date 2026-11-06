v5 reading — shared-input primary-model experiment (E2) and training-budget experiment (E4), shared-input reading

PhysioGraph-GRU is an organ graph model with gated recurrent unit (GRU) nodes. The v5 shared-input PhysioGraph-GRU grid selects learning rate 0.001000 and large width using A-validation pooled masked root mean squared error (RMSE). The selected no-edge model and admissible-edge model have similar pooled errors across four training seeds; these data do not establish a consistent benefit from the admissible topology. At the longer schedules, the no-edge model's comparison with GRU-D, a GRU baseline with learned decay for missing observations, changes, while the admissible model retains a deficit. All comparisons with Table 1 are descriptive: Table 1 models were tuned in the v4 series, and its learned-graph baselines used paper hyperparameters. This v5 reading does not establish a universally preferred backbone.

A-validation selects checkpoints and the shared-input configuration; A-test is the internal holdout and B is the external holdout. Each seed's pooled RMSE is the square root of observed squared error summed over stays, forecast hours and variables, divided by the number of observed target entries. Per-organ RMSE uses that calculation within an organ slice. Errors are in A-training standard-deviation units. The context and forecast are each 12 hours. Mean ± standard deviation (SD) uses the sample SD across seeds 0–3. Every difference is target minus reference: negative values favor the target. Sign counts are negative/zero/positive across the four exact, unrounded differences. The 95% paired Student t confidence interval (CI) is mean difference ± 3.182446 × sample SD / √4, with three degrees of freedom. These exploratory intervals describe variation over training seeds; they do not estimate patient-sampling uncertainty or adjust for the many contrasts. Pairing uses seed identity and the same frozen clinical splits; different architectures need not have identical random-number trajectories.

Numerical provenance is in [e2_e4_summary.json](e2_e4_summary.json), a JavaScript Object Notation (JSON) file. Raw-run row identifiers map every numeric field to an absolute source file, Secure Hash Algorithm 256-bit (SHA-256) hash and JSON pointer. Aggregate entries list their input row identifiers; paired entries identify both sets of inputs and use the formula above. The JSON's `sources[*].exact_fields` preserves original floating-point tokens as strings, while reported numerical values and this reading use six decimals, computed before rounding. The 35-epoch shared-input rows belong to v5; the 35-epoch GRU-D and Table 1 comparisons remain explicitly frozen v4 references. The original REPRODUCTION_NOTE describes the runner build and smoke evidence. The present reading uses the later full-scope host run records, without performing training or new inference.

**Table 1. v5 no-edge grid, seed 0**

| ID | Configuration | Status | Epochs done | Best epoch | Parameters | A-val RMSE | A-test RMSE | B RMSE | Selection |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| G01 | lr0.0005_large | complete | 35 | 35 | 778384 | 0.769421 | 0.756991 | 0.811263 |  |
| G02 | lr0.0005_small | complete | 35 | 35 | 355088 | 0.774048 | 0.760283 | 0.812902 |  |
| G03 | lr0.001_large | complete | 35 | 35 | 778384 | 0.766727 | 0.755223 | 0.808853 | selected |
| G04 | lr0.001_small | complete | 35 | 35 | 355088 | 0.767649 | 0.755170 | 0.809601 |  |
| G05 | lr0.002_large | complete | 35 | 35 | 778384 | 0.769964 | 0.760575 | 0.810334 |  |
| G06 | lr0.002_small | complete | 35 | 33 | 355088 | 0.767992 | 0.758075 | 0.809475 |  |

All six grid cells completed at the 35-epoch cap. The selection record chooses `lr0.001_large`: learning rate 0.001000, organ width 96, baseline hidden width 256, state size 48 and two layers; its A-validation RMSE is 0.766727. A-test and B were evaluated after the A-validation checkpoint was restored and did not select the configuration. Executing the original `select_grid` function in isolation reproduced the selection; replacing all grid A-test and B metrics with adversarial values left it unchanged, and an equal-validation probe confirmed the lexical tie break. The selection record's six embedded records and hashes match the six source run files. The displayed holdout columns are descriptive and do not rank grid choices.

**Table 2. v5 arm records: ten arms × four seeds**

| ID | Arm | Seed | Status | Done/cap | Best epoch | Parameters | A-val RMSE | A-test RMSE | B RMSE |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A01 | none | 0 | complete | 35/35 | 35 | 778384 | 0.766727 | 0.755223 | 0.808853 |
| A02 | none | 1 | complete | 35/35 | 34 | 778384 | 0.765883 | 0.754226 | 0.806079 |
| A03 | none | 2 | complete | 35/35 | 34 | 778384 | 0.769977 | 0.758002 | 0.810140 |
| A04 | none | 3 | complete | 35/35 | 34 | 778384 | 0.768139 | 0.756266 | 0.810196 |
| A05 | none_norm | 0 | complete | 35/35 | 35 | 778384 | 0.768848 | 0.759139 | 0.811049 |
| A06 | none_norm | 1 | complete | 35/35 | 34 | 778384 | 0.766433 | 0.757045 | 0.805617 |
| A07 | none_norm | 2 | complete | 35/35 | 34 | 778384 | 0.771117 | 0.760269 | 0.810973 |
| A08 | none_norm | 3 | complete | 35/35 | 34 | 778384 | 0.767589 | 0.757506 | 0.810627 |
| A09 | none_pmatch | 0 | complete | 35/35 | 33 | 930464 | 0.768004 | 0.756771 | 0.808883 |
| A10 | none_pmatch | 1 | complete | 35/35 | 34 | 930464 | 0.765575 | 0.756591 | 0.807586 |
| A11 | none_pmatch | 2 | complete | 35/35 | 34 | 930464 | 0.767955 | 0.755471 | 0.808145 |
| A12 | none_pmatch | 3 | complete | 35/35 | 34 | 930464 | 0.767187 | 0.756571 | 0.809439 |
| A13 | admissible | 0 | complete | 35/35 | 35 | 930464 | 0.769251 | 0.757398 | 0.811164 |
| A14 | admissible | 1 | complete | 35/35 | 34 | 930464 | 0.768204 | 0.755760 | 0.809495 |
| A15 | admissible | 2 | complete | 35/35 | 34 | 930464 | 0.767399 | 0.755938 | 0.809211 |
| A16 | admissible | 3 | complete | 35/35 | 34 | 930464 | 0.762109 | 0.751186 | 0.807203 |
| A17 | dense | 0 | complete | 35/35 | 35 | 1006504 | 0.772171 | 0.756101 | 0.811213 |
| A18 | dense | 1 | complete | 35/35 | 32 | 1006504 | 0.767425 | 0.755052 | 0.809367 |
| A19 | dense | 2 | complete | 35/35 | 34 | 1006504 | 0.770519 | 0.756700 | 0.812594 |
| A20 | dense | 3 | complete | 35/35 | 34 | 1006504 | 0.770267 | 0.754318 | 0.810419 |
| A21 | reversed | 0 | complete | 35/35 | 34 | 930464 | 0.766100 | 0.755957 | 0.810358 |
| A22 | reversed | 1 | complete | 35/35 | 34 | 930464 | 0.766195 | 0.753724 | 0.810005 |
| A23 | reversed | 2 | complete | 35/35 | 34 | 930464 | 0.768692 | 0.753639 | 0.810458 |
| A24 | reversed | 3 | complete | 35/35 | 34 | 930464 | 0.767024 | 0.751982 | 0.809395 |
| A25 | random_s0 | 0 | complete | 35/35 | 34 | 930464 | 0.766260 | 0.753705 | 0.808871 |
| A26 | random_s0 | 1 | complete | 35/35 | 34 | 930464 | 0.767229 | 0.754442 | 0.810718 |
| A27 | random_s0 | 2 | complete | 35/35 | 34 | 930464 | 0.766004 | 0.752476 | 0.809756 |
| A28 | random_s0 | 3 | complete | 35/35 | 34 | 930464 | 0.765810 | 0.751976 | 0.807377 |
| A29 | random_s1 | 0 | complete | 35/35 | 35 | 930464 | 0.770253 | 0.756954 | 0.810790 |
| A30 | random_s1 | 1 | complete | 35/35 | 34 | 930464 | 0.768311 | 0.757126 | 0.811206 |
| A31 | random_s1 | 2 | complete | 35/35 | 34 | 930464 | 0.772836 | 0.757348 | 0.812172 |
| A32 | random_s1 | 3 | complete | 35/35 | 34 | 930464 | 0.763717 | 0.752262 | 0.808692 |
| A33 | random_s2 | 0 | complete | 35/35 | 34 | 930464 | 0.766940 | 0.753397 | 0.809773 |
| A34 | random_s2 | 1 | complete | 35/35 | 34 | 930464 | 0.767972 | 0.756862 | 0.810955 |
| A35 | random_s2 | 2 | complete | 35/35 | 34 | 930464 | 0.769042 | 0.754655 | 0.808893 |
| A36 | random_s2 | 3 | complete | 35/35 | 34 | 930464 | 0.763047 | 0.748250 | 0.806121 |
| A37 | misspecified-1 | 0 | complete | 35/35 | 35 | 930464 | 0.767272 | 0.755666 | 0.809858 |
| A38 | misspecified-1 | 1 | complete | 35/35 | 34 | 930464 | 0.767782 | 0.754005 | 0.810232 |
| A39 | misspecified-1 | 2 | complete | 35/35 | 34 | 930464 | 0.768782 | 0.754829 | 0.810145 |
| A40 | misspecified-1 | 3 | complete | 35/35 | 34 | 930464 | 0.764630 | 0.752897 | 0.807107 |

All 40 arm fits completed with finite A-test and B predictions, and none stopped before the 35-epoch cap. All arms use the shared grid selection without separate arm tuning. `none` and `none_norm` each have 778384 parameters; every eight-edge arm and `none_pmatch` has 930464; dense has 1006504. The selected grid cell and the independently recorded `none` seed-0 arm have exactly equal pooled validation, A-test and B RMSEs. They supply one seed-0 outcome, not an additional replicate.

**Table 3. v5 per-organ RMSE for every arm record; tuple order cardiovascular / pulmonary / renal / metabolic**

| ID | Arm | Seed | A-validation organs | A-test organs | B organs |
| --- | --- | --- | --- | --- | --- |
| A01 | none | 0 | 0.707710 / 0.810622 / 0.686696 / 0.925169 | 0.696748 / 0.832036 / 0.693855 / 0.805489 | 0.799068 / 0.812865 / 0.925089 / 0.822021 |
| A02 | none | 1 | 0.705438 / 0.810313 / 0.685357 / 0.928535 | 0.694047 / 0.832289 / 0.699322 / 0.805941 | 0.793996 / 0.814477 / 0.926717 / 0.818661 |
| A03 | none | 2 | 0.707352 / 0.813324 / 0.682501 / 0.946056 | 0.695238 / 0.835728 / 0.695789 / 0.824472 | 0.797580 / 0.813874 / 0.923052 / 0.839848 |
| A04 | none | 3 | 0.706524 / 0.810159 / 0.691912 / 0.940990 | 0.696050 / 0.829666 / 0.703038 / 0.822896 | 0.798907 / 0.813081 / 0.927382 / 0.834230 |
| A05 | none_norm | 0 | 0.706353 / 0.811578 / 0.708667 / 0.938928 | 0.696873 / 0.835494 / 0.717919 / 0.821606 | 0.799143 / 0.812941 / 0.943388 / 0.836917 |
| A06 | none_norm | 1 | 0.704564 / 0.814596 / 0.693375 / 0.922242 | 0.693442 / 0.839980 / 0.707149 / 0.806339 | 0.793703 / 0.814798 / 0.930085 / 0.814105 |
| A07 | none_norm | 2 | 0.707829 / 0.816307 / 0.697689 / 0.941069 | 0.695012 / 0.840425 / 0.711660 / 0.825677 | 0.798331 / 0.814708 / 0.938491 / 0.837193 |
| A08 | none_norm | 3 | 0.706542 / 0.810556 / 0.689067 / 0.936197 | 0.696050 / 0.831792 / 0.702463 / 0.827253 | 0.798879 / 0.813534 / 0.928648 / 0.836837 |
| A09 | none_pmatch | 0 | 0.707108 / 0.813992 / 0.689957 / 0.927494 | 0.697471 / 0.833324 / 0.701958 / 0.809621 | 0.797482 / 0.812411 / 0.928352 / 0.831198 |
| A10 | none_pmatch | 1 | 0.706230 / 0.812600 / 0.713744 / 0.908774 | 0.695579 / 0.834439 / 0.726988 / 0.804926 | 0.795319 / 0.812664 / 0.958130 / 0.821826 |
| A11 | none_pmatch | 2 | 0.707426 / 0.817108 / 0.682812 / 0.918924 | 0.694090 / 0.836615 / 0.694138 / 0.804315 | 0.797472 / 0.814913 / 0.924291 / 0.818721 |
| A12 | none_pmatch | 3 | 0.709017 / 0.815185 / 0.675146 / 0.913840 | 0.697149 / 0.835787 / 0.686505 / 0.805768 | 0.799479 / 0.813666 / 0.917862 / 0.825093 |
| A13 | admissible | 0 | 0.705786 / 0.809216 / 0.734460 / 0.943796 | 0.695347 / 0.829356 / 0.745716 / 0.823859 | 0.797949 / 0.813689 / 0.965521 / 0.836257 |
| A14 | admissible | 1 | 0.705301 / 0.808894 / 0.704531 / 0.946374 | 0.695577 / 0.827787 / 0.718683 / 0.821752 | 0.795992 / 0.814257 / 0.942911 / 0.835978 |
| A15 | admissible | 2 | 0.707657 / 0.809938 / 0.710140 / 0.926412 | 0.695098 / 0.831101 / 0.724698 / 0.812836 | 0.796296 / 0.815160 / 0.948127 / 0.827860 |
| A16 | admissible | 3 | 0.703664 / 0.807095 / 0.704612 / 0.908978 | 0.691892 / 0.825863 / 0.723700 / 0.801505 | 0.793698 / 0.813393 / 0.938199 / 0.830545 |
| A17 | dense | 0 | 0.705968 / 0.809869 / 0.735476 / 0.963951 | 0.695759 / 0.826185 / 0.737224 / 0.823390 | 0.797145 / 0.813800 / 0.961425 / 0.841832 |
| A18 | dense | 1 | 0.706789 / 0.809556 / 0.734835 / 0.924263 | 0.694952 / 0.827159 / 0.734286 / 0.815320 | 0.794457 / 0.814579 / 0.962792 / 0.836616 |
| A19 | dense | 2 | 0.706616 / 0.809832 / 0.745063 / 0.945998 | 0.695741 / 0.826644 / 0.748252 / 0.823830 | 0.798498 / 0.814719 / 0.970063 / 0.842573 |
| A20 | dense | 3 | 0.707323 / 0.810269 / 0.746055 / 0.939786 | 0.693592 / 0.825309 / 0.744672 / 0.817376 | 0.794442 / 0.813337 / 0.978035 / 0.845388 |
| A21 | reversed | 0 | 0.705009 / 0.806703 / 0.732994 / 0.929087 | 0.695251 / 0.825713 / 0.750231 / 0.821700 | 0.795095 / 0.813432 / 0.970348 / 0.843297 |
| A22 | reversed | 1 | 0.703841 / 0.808317 / 0.711293 / 0.935890 | 0.695664 / 0.823629 / 0.730127 / 0.813017 | 0.795731 / 0.813583 / 0.953571 / 0.840925 |
| A23 | reversed | 2 | 0.705941 / 0.809316 / 0.742999 / 0.936102 | 0.694610 / 0.825117 / 0.741173 / 0.808545 | 0.796595 / 0.813788 / 0.974221 / 0.834235 |
| A24 | reversed | 3 | 0.704875 / 0.809886 / 0.715285 / 0.933044 | 0.693528 / 0.822145 / 0.735762 / 0.809786 | 0.794949 / 0.814107 / 0.950282 / 0.838966 |
| A25 | random_s0 | 0 | 0.705442 / 0.807888 / 0.730211 / 0.926155 | 0.694122 / 0.824237 / 0.739923 / 0.814542 | 0.796551 / 0.812982 / 0.962056 / 0.825254 |
| A26 | random_s0 | 1 | 0.706011 / 0.809196 / 0.741411 / 0.924897 | 0.695719 / 0.824657 / 0.752543 / 0.808709 | 0.796082 / 0.813851 / 0.978325 / 0.838046 |
| A27 | random_s0 | 2 | 0.706855 / 0.808360 / 0.719099 / 0.920302 | 0.695929 / 0.823449 / 0.730252 / 0.801103 | 0.797498 / 0.814078 / 0.950589 / 0.828699 |
| A28 | random_s0 | 3 | 0.705414 / 0.809776 / 0.707797 / 0.923559 | 0.694891 / 0.821976 / 0.726152 / 0.807305 | 0.794238 / 0.812804 / 0.940663 / 0.830165 |
| A29 | random_s1 | 0 | 0.707573 / 0.808700 / 0.718665 / 0.950544 | 0.695441 / 0.829635 / 0.726508 / 0.824619 | 0.796616 / 0.812799 / 0.952439 / 0.845834 |
| A30 | random_s1 | 1 | 0.705352 / 0.810736 / 0.705447 / 0.941723 | 0.695288 / 0.831655 / 0.724607 / 0.820896 | 0.797845 / 0.814028 / 0.947065 / 0.841392 |
| A31 | random_s1 | 2 | 0.708650 / 0.810333 / 0.752634 / 0.952967 | 0.695915 / 0.827649 / 0.758600 / 0.822300 | 0.798049 / 0.813878 / 0.982381 / 0.839822 |
| A32 | random_s1 | 3 | 0.704298 / 0.807427 / 0.706390 / 0.918064 | 0.693670 / 0.824346 / 0.720249 / 0.809425 | 0.795429 / 0.813820 / 0.943814 / 0.832452 |
| A33 | random_s2 | 0 | 0.707566 / 0.808494 / 0.717750 / 0.925040 | 0.696384 / 0.822822 / 0.732951 / 0.808613 | 0.796959 / 0.814057 / 0.944593 / 0.833462 |
| A34 | random_s2 | 1 | 0.703754 / 0.808832 / 0.752149 / 0.937591 | 0.694391 / 0.829838 / 0.762259 / 0.816337 | 0.795663 / 0.813357 / 0.984859 / 0.841906 |
| A35 | random_s2 | 2 | 0.707656 / 0.810431 / 0.712678 / 0.937500 | 0.695776 / 0.825358 / 0.724827 / 0.816944 | 0.796941 / 0.814032 / 0.950903 / 0.823664 |
| A36 | random_s2 | 3 | 0.703511 / 0.808623 / 0.714787 / 0.910059 | 0.693371 / 0.821886 / 0.715639 / 0.783734 | 0.793418 / 0.813158 / 0.939562 / 0.822205 |
| A37 | misspecified-1 | 0 | 0.705235 / 0.809956 / 0.719158 / 0.932370 | 0.694472 / 0.828844 / 0.739823 / 0.815711 | 0.796450 / 0.814399 / 0.956431 / 0.832799 |
| A38 | misspecified-1 | 1 | 0.705646 / 0.808132 / 0.699427 / 0.945153 | 0.694477 / 0.825275 / 0.711416 / 0.821208 | 0.796487 / 0.813820 / 0.936123 / 0.843126 |
| A39 | misspecified-1 | 2 | 0.708099 / 0.809811 / 0.719686 / 0.933514 | 0.696052 / 0.825435 / 0.737465 / 0.813065 | 0.797185 / 0.814038 / 0.953488 / 0.833305 |
| A40 | misspecified-1 | 3 | 0.705894 / 0.807974 / 0.721917 / 0.913285 | 0.694759 / 0.822580 / 0.731065 / 0.812672 | 0.793805 / 0.813154 / 0.954851 / 0.825108 |

Each tuple follows the same four organ slices and uses observed-entry pooling within its own organ. These are not averaged to obtain the pooled metric: organs contribute different numbers of observed targets. The renal A-test and B values feed the persistence comparison below; the other organ values remain available here and in the JSON so that a pooled change is not mistaken for a uniform organ-level change.

**Table 4. v5 four-seed arm summaries**

| Arm | A-test mean ± SD | B mean ± SD |
| --- | --- | --- |
| none | 0.755929 ± 0.001613 | 0.808817 ± 0.001928 |
| none_norm | 0.758490 ± 0.001488 | 0.809567 ± 0.002639 |
| none_pmatch | 0.756351 ± 0.000593 | 0.808513 ± 0.000814 |
| admissible | 0.755070 ± 0.002692 | 0.809268 ± 0.001624 |
| dense | 0.755543 ± 0.001063 | 0.810898 ± 0.001360 |
| reversed | 0.753826 ± 0.001632 | 0.810054 ± 0.000481 |
| random_s0 | 0.753149 ± 0.001127 | 0.809180 ± 0.001419 |
| random_s1 | 0.755923 ± 0.002445 | 0.810715 ± 0.001468 |
| random_s2 | 0.753291 ± 0.003653 | 0.808935 ± 0.002058 |
| misspecified-1 | 0.754349 ± 0.001182 | 0.809335 ± 0.001494 |

The no-edge means are 0.755929 on A-test and 0.808817 on B; the admissible means are 0.755070 and 0.809268. The small change in the two directions motivates the paired comparisons rather than an ordering based only on means. Adding normalization without edges yields 0.758490 and 0.809567; matching the admissible parameter count without edges yields 0.756351 and 0.808513. Random-draw means also vary, so an individual random topology is not a sufficient summary of topology sensitivity.

**Table 5. v5 paired differences against raw empty edges**

| Target | Split | Δ mean ± SD | 95% paired t CI | Signs −/0/+ |
| --- | --- | --- | --- | --- |
| none_norm | A_test | +0.002561 ± 0.001116 | [+0.000785, +0.004336] | 0/0/4 |
| none_norm | B | +0.000750 ± 0.001106 | [-0.001010, +0.002509] | 1/0/3 |
| none_pmatch | A_test | +0.000422 ± 0.002143 | [-0.002987, +0.003831] | 1/0/3 |
| none_pmatch | B | -0.000304 ± 0.001467 | [-0.002638, +0.002030] | 2/0/2 |
| admissible | A_test | -0.000859 ± 0.003376 | [-0.006231, +0.004514] | 2/0/2 |
| admissible | B | +0.000451 ± 0.002945 | [-0.004235, +0.005137] | 2/0/2 |
| dense | A_test | -0.000386 ± 0.001454 | [-0.002700, +0.001928] | 2/0/2 |
| dense | B | +0.002081 ± 0.001307 | [+0.000001, +0.004161] | 0/0/4 |
| reversed | A_test | -0.002103 ± 0.002613 | [-0.006261, +0.002054] | 3/0/1 |
| reversed | B | +0.001237 ± 0.002025 | [-0.001985, +0.004459] | 1/0/3 |
| random_s0 | A_test | -0.002780 ± 0.002607 | [-0.006928, +0.001368] | 3/0/1 |
| random_s0 | B | +0.000363 ± 0.003114 | [-0.004592, +0.005318] | 2/0/2 |
| random_s1 | A_test | -0.000006 ± 0.003047 | [-0.004855, +0.004843] | 2/0/2 |
| random_s1 | B | +0.001898 ± 0.002709 | [-0.002412, +0.006209] | 1/0/3 |
| random_s2 | A_test | -0.002638 ± 0.004393 | [-0.009628, +0.004352] | 3/0/1 |
| random_s2 | B | +0.000118 ± 0.003774 | [-0.005887, +0.006123] | 2/0/2 |
| misspecified-1 | A_test | -0.001580 ± 0.001973 | [-0.004719, +0.001559] | 3/0/1 |
| misspecified-1 | B | +0.000518 ± 0.002985 | [-0.004231, +0.005268] | 1/0/3 |

Admissible minus `none` is −0.000859 on A-test (CI [−0.006231, +0.004514]) and +0.000451 on B (CI [−0.004235, +0.005137]); both have two negative and two positive seed differences. This contrast combines messages, active coupling normalization and added parameters. It does not isolate the prior's content. The normalization-only control raises A-test error by +0.002561 (CI [+0.000785, +0.004336]); most edge contrasts include zero, while the dense B interval has a lower bound of +0.000001. That narrow exploratory exclusion must be read with the small seed count and multiple comparisons.

**Table 6. v5 paired differences against normalization-retaining empty edges**

| Target | Split | Δ mean ± SD | 95% paired t CI | Signs −/0/+ |
| --- | --- | --- | --- | --- |
| admissible | A_test | -0.003420 ± 0.002353 | [-0.007164, +0.000325] | 4/0/0 |
| admissible | B | -0.000299 ± 0.003137 | [-0.005290, +0.004693] | 2/0/2 |
| dense | A_test | -0.002947 ± 0.000674 | [-0.004019, -0.001874] | 4/0/0 |
| dense | B | +0.001332 ± 0.001795 | [-0.001525, +0.004188] | 1/0/3 |
| reversed | A_test | -0.004664 ± 0.001694 | [-0.007359, -0.001969] | 4/0/0 |
| reversed | B | +0.000487 ± 0.002618 | [-0.003679, +0.004653] | 3/0/1 |
| random_s0 | A_test | -0.005340 ± 0.002126 | [-0.008723, -0.001958] | 4/0/0 |
| random_s0 | B | -0.000386 ± 0.003751 | [-0.006355, +0.005582] | 3/0/1 |
| random_s1 | A_test | -0.002567 ± 0.002194 | [-0.006059, +0.000925] | 3/0/1 |
| random_s1 | B | +0.001148 ± 0.003225 | [-0.003983, +0.006280] | 2/0/2 |
| random_s2 | A_test | -0.005199 ± 0.003746 | [-0.011159, +0.000761] | 4/0/0 |
| random_s2 | B | -0.000631 ± 0.004209 | [-0.007330, +0.006067] | 3/0/1 |
| misspecified-1 | A_test | -0.004141 ± 0.001090 | [-0.005875, -0.002406] | 4/0/0 |
| misspecified-1 | B | -0.000231 ± 0.003444 | [-0.005711, +0.005248] | 3/0/1 |

`none_norm` activates the same coupling layer normalization (LayerNorm) operation with zero message sum, addressing the normalization bypass in raw `none`. Admissible minus `none_norm` is −0.003420 on A-test (CI [−0.007164, +0.000325]) and −0.000299 on B (CI [−0.005290, +0.004693]). Several alternative topologies also improve A-test relative to this control, and every B interval in this table includes zero. This reference controls normalization behavior but leaves the extra edge parameters unmatched; it therefore does not establish a benefit specific to the admissible topology.

**Table 7. v5 paired differences against the exact parameter-count control**

| Target | Split | Δ mean ± SD | 95% paired t CI | Signs −/0/+ |
| --- | --- | --- | --- | --- |
| admissible | A_test | -0.001281 ± 0.002813 | [-0.005757, +0.003195] | 2/0/2 |
| admissible | B | +0.000755 ± 0.002058 | [-0.002519, +0.004029] | 1/0/3 |
| reversed | A_test | -0.002525 ± 0.001611 | [-0.005088, +0.000037] | 4/0/0 |
| reversed | B | +0.001541 ± 0.001138 | [-0.000270, +0.003351] | 1/0/3 |
| random_s0 | A_test | -0.003202 ± 0.001018 | [-0.004822, -0.001581] | 4/0/0 |
| random_s0 | B | +0.000667 ± 0.002227 | [-0.002877, +0.004210] | 2/0/2 |
| random_s1 | A_test | -0.000428 ± 0.002688 | [-0.004705, +0.003848] | 1/0/3 |
| random_s1 | B | +0.002202 ± 0.002170 | [-0.001251, +0.005654] | 1/0/3 |
| random_s2 | A_test | -0.003060 ± 0.003826 | [-0.009147, +0.003027] | 3/0/1 |
| random_s2 | B | +0.000422 ± 0.002769 | [-0.003984, +0.004828] | 1/0/3 |
| misspecified-1 | A_test | -0.002002 ± 0.001389 | [-0.004212, +0.000208] | 4/0/0 |
| misspecified-1 | B | +0.000822 ± 0.002213 | [-0.002699, +0.004343] | 1/0/3 |

`none_pmatch` matches the 930464 total parameters of every eight-edge arm by adding active nonlinear input-projection branches. Admissible minus this reference is −0.001281 on A-test (CI [−0.005757, +0.003195]) and +0.000755 on B (CI [−0.002519, +0.004029]). All B intervals include zero. Dense is omitted because its parameter count is larger and this reference is not capacity matched to it. Matching counts does not match computation or function class, and `none_pmatch` retains the empty-edge normalization bypass; the normalization and capacity controls answer separate confounds rather than jointly holding both fixed.

**Table 8. v5 random topologies and overlap with admissible edges**

| Arm | Draw seed | Intersection | Union | Jaccard | A-test mean ± SD | B mean ± SD |
| --- | --- | --- | --- | --- | --- | --- |
| random_s0 | 0 | 5 | 11 | 0.454545 | 0.753149 ± 0.001127 | 0.809180 ± 0.001419 |
| random_s1 | 1 | 6 | 10 | 0.600000 | 0.755923 ± 0.002445 | 0.810715 ± 0.001468 |
| random_s2 | 2 | 5 | 11 | 0.454545 | 0.753291 ± 0.003653 | 0.808935 ± 0.002058 |

Jaccard overlap is the number of shared directed edges divided by the number in their union. The three fixed draw seeds give overlaps 0.454545, 0.600000 and 0.454545; each graph has eight edges from the twelve directed non-self possibilities, so any two such eight-edge sets must share at least four edges. Draw identity is independent of training seed, each draw is fixed across all four fits, and `random_s0` agrees with the frozen original random graph. These are substantially overlapping controls, and none was chosen or rejected using a model score.

**Table 9. v5 spread across the three graph draws**

| Quantity | Draws | Across-draw mean ± SD | Minimum | Maximum | Range |
| --- | --- | --- | --- | --- | --- |
| Jaccard overlap | 3 | 0.503030 ± 0.083978 | 0.454545 | 0.600000 | 0.145455 |
| A-test four-seed draw means | 3 | 0.754121 ± 0.001562 | 0.753149 | 0.755923 | 0.002773 |
| B four-seed draw means | 3 | 0.809610 ± 0.000965 | 0.808935 | 0.810715 | 0.001780 |

The A-test draw means span 0.753149–0.755923, a range of 0.002773; B spans 0.808935–0.810715, a range of 0.001780. The standard deviations in this table describe three graph draws after averaging their four training seeds, whereas Table 8's standard deviations describe training variation within each draw. The JSON also gives the draw spread at each matched training seed. The twelve model fits are not twelve independent topology draws, and overlap spread alone does not identify a relationship between prior similarity and forecasting error.

**Table 10. v5 random draw minus admissible topology**

| Target | Split | Δ mean ± SD | 95% paired t CI | Signs −/0/+ |
| --- | --- | --- | --- | --- |
| random_s0 | A_test | -0.001921 ± 0.002100 | [-0.005262, +0.001420] | 3/0/1 |
| random_s0 | B | -0.000088 ± 0.001533 | [-0.002527, +0.002351] | 1/0/3 |
| random_s1 | A_test | +0.000852 ± 0.000877 | [-0.000543, +0.002248] | 1/0/3 |
| random_s1 | B | +0.001447 ± 0.001376 | [-0.000742, +0.003636] | 1/0/3 |
| random_s2 | A_test | -0.001779 ± 0.002223 | [-0.005317, +0.001758] | 3/0/1 |
| random_s2 | B | -0.000333 ± 0.001277 | [-0.002365, +0.001699] | 3/0/1 |

Each random topology is compared with admissible at the same training seed, shared-input configuration, edge count and parameter count. All six intervals include zero. The random-draw A-test means fall on both sides of admissible, and two B means are slightly lower while one is higher. These runs do not support an admissible-topology advantage over the sampled overlapping alternatives.

**Table 11. v5 shared-input models beside frozen Table 1 references**

| Series | Model | Configuration | A-test mean ± SD | B mean ± SD |
| --- | --- | --- | --- | --- |
| v5 | shared-input none | lr0.001_large | 0.755929 ± 0.001613 | 0.808817 ± 0.001928 |
| v5 | shared-input none_norm | lr0.001_large | 0.758490 ± 0.001488 | 0.809567 ± 0.002639 |
| v5 | shared-input admissible | lr0.001_large | 0.755070 ± 0.002692 | 0.809268 ± 0.001624 |
| frozen v4 | GRU-D | lr0.0005_large | 0.745811 ± 0.000489 | 0.805874 ± 0.000886 |
| frozen v4 | GRU | lr0.001_large | 0.748858 ± 0.000682 | 0.805883 ± 0.000694 |
| frozen v4 | GraphGRU (learned graph) | lr0.0005_large | 0.754937 ± 0.002374 | 0.811845 ± 0.002430 |
| frozen v4 | t-PatchGNN (learned graph) | paper hyperparameters | 0.749155 ± 0.001628 | 0.793921 ± 0.000937 |
| frozen v4 | GraFITi v3 (learned graph) | paper hyperparameters | 0.748258 ± 0.000330 | 0.793230 ± 0.000109 |
| frozen v4 | partitioned-input PhysioGraph-GRU (context) | lr0.0005_large | 0.770165 ± 0.002211 | 0.817699 ± 0.001014 |

The shared-input v5 means are lower than the frozen partitioned-input PhysioGraph-GRU context row, but remain above GRU-D, GRU, t-PatchGNN and GraFITi means on both holdouts. GraphGRU is close on A-test and higher on B than the three displayed v5 rows. The baseline comparisons are descriptive because the Table 1 models were tuned in the v4 series, the shared-input model is retuned in v5, and the learned graphs used paper hyperparameters. Exact pooled values were recovered from the frozen run lineage because the human summary is rounded and `stats_v4.json`'s selected-model mean-stay summaries estimate a different quantity. The context row is not reclassified as a v5 fit.

**Table 12. v5 headline models minus frozen Table 1 comparators, seed-index paired**

| v5 target | v4 reference | Split | Δ mean ± SD | 95% paired t CI | Signs −/0/+ |
| --- | --- | --- | --- | --- | --- |
| none | grud | A_test | +0.010118 ± 0.001803 | [+0.007249, +0.012987] | 0/0/4 |
| none | grud | B | +0.002943 ± 0.001659 | [+0.000302, +0.005583] | 0/0/4 |
| none | gru | A_test | +0.007071 ± 0.001703 | [+0.004360, +0.009781] | 0/0/4 |
| none | gru | B | +0.002934 ± 0.002396 | [-0.000879, +0.006747] | 1/0/3 |
| none | graphgru | A_test | +0.000992 ± 0.003010 | [-0.003798, +0.005783] | 2/0/2 |
| none | graphgru | B | -0.003028 ± 0.003321 | [-0.008312, +0.002257] | 3/0/1 |
| none | tpatchgnn | A_test | +0.006774 ± 0.002422 | [+0.002920, +0.010628] | 0/0/4 |
| none | tpatchgnn | B | +0.014896 ± 0.001596 | [+0.012356, +0.017436] | 0/0/4 |
| none | grafiti | A_test | +0.007671 ± 0.001779 | [+0.004841, +0.010502] | 0/0/4 |
| none | grafiti | B | +0.015587 ± 0.001878 | [+0.012599, +0.018575] | 0/0/4 |
| none_norm | grud | A_test | +0.012679 ± 0.001617 | [+0.010107, +0.015252] | 0/0/4 |
| none_norm | grud | B | +0.003692 ± 0.002533 | [-0.000338, +0.007722] | 0/0/4 |
| none_norm | gru | A_test | +0.009632 ± 0.001807 | [+0.006757, +0.012506] | 0/0/4 |
| none_norm | gru | B | +0.003684 ± 0.003105 | [-0.001257, +0.008624] | 1/0/3 |
| none_norm | graphgru | A_test | +0.003553 ± 0.003613 | [-0.002195, +0.009302] | 0/0/4 |
| none_norm | graphgru | B | -0.002278 ± 0.004373 | [-0.009237, +0.004681] | 3/0/1 |
| none_norm | tpatchgnn | A_test | +0.009334 ± 0.002262 | [+0.005736, +0.012933] | 0/0/4 |
| none_norm | tpatchgnn | B | +0.015646 ± 0.001939 | [+0.012561, +0.018731] | 0/0/4 |
| none_norm | grafiti | A_test | +0.010232 ± 0.001486 | [+0.007867, +0.012597] | 0/0/4 |
| none_norm | grafiti | B | +0.016337 ± 0.002592 | [+0.012212, +0.020461] | 0/0/4 |
| admissible | grud | A_test | +0.009260 ± 0.002502 | [+0.005279, +0.013240] | 0/0/4 |
| admissible | grud | B | +0.003394 ± 0.002438 | [-0.000486, +0.007273] | 0/0/4 |
| admissible | gru | A_test | +0.006212 ± 0.002920 | [+0.001566, +0.010858] | 0/0/4 |
| admissible | gru | B | +0.003385 ± 0.001525 | [+0.000959, +0.005811] | 0/0/4 |
| admissible | graphgru | A_test | +0.000134 ± 0.004866 | [-0.007610, +0.007877] | 2/0/2 |
| admissible | graphgru | B | -0.002577 ± 0.003698 | [-0.008461, +0.003308] | 3/0/1 |
| admissible | tpatchgnn | A_test | +0.005915 ± 0.003470 | [+0.000394, +0.011436] | 0/0/4 |
| admissible | tpatchgnn | B | +0.015347 ± 0.001370 | [+0.013167, +0.017528] | 0/0/4 |
| admissible | grafiti | A_test | +0.006813 ± 0.002406 | [+0.002983, +0.010642] | 0/0/4 |
| admissible | grafiti | B | +0.016038 ± 0.001613 | [+0.013471, +0.018605] | 0/0/4 |

At A-test, all three v5 targets have positive differences in every seed against GRU-D, GRU and both paper-hyperparameter learned graphs. Their B differences against t-PatchGNN and GraFITi are also positive in every seed. Against GRU-D, `none` is +0.010118 on A-test (CI [+0.007249, +0.012987]) and +0.002943 on B (CI [+0.000302, +0.005583]); admissible is +0.009260 and +0.003394, with its B interval crossing zero. Seed identity allows these arithmetic paired summaries, but does not remove the v4-versus-v5 tuning difference or create a common random trajectory across architectures. These are descriptive comparisons with the frozen v4 tuning caveat.

**Table 13. v5 renal RMSE against persistence**

| Arm | A-test mean ± SD | A-test Δ ± SD | A-test CI | A-test signs | B mean ± SD | B Δ ± SD | B CI | B signs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| none | 0.698001 ± 0.004050 | -0.064486 ± 0.004050 | [-0.070930, -0.058042] | 4/0/0 | 0.925560 ± 0.001930 | -0.051490 ± 0.001930 | [-0.054560, -0.048419] | 4/0/0 |
| none_norm | 0.709798 ± 0.006589 | -0.052689 ± 0.006589 | [-0.063173, -0.042204] | 4/0/0 | 0.935153 ± 0.006999 | -0.041897 ± 0.006999 | [-0.053033, -0.030760] | 4/0/0 |
| none_pmatch | 0.702397 ± 0.017566 | -0.060089 ± 0.017566 | [-0.088040, -0.032138] | 4/0/0 | 0.932159 ± 0.017845 | -0.044891 ± 0.017845 | [-0.073286, -0.016495] | 4/0/0 |
| admissible | 0.728199 ± 0.011971 | -0.034287 ± 0.011971 | [-0.053336, -0.015239] | 4/0/0 | 0.948689 ± 0.011931 | -0.028360 ± 0.011931 | [-0.047345, -0.009375] | 4/0/0 |
| dense | 0.741109 ± 0.006464 | -0.021378 ± 0.006464 | [-0.031664, -0.011092] | 4/0/0 | 0.968079 ± 0.007644 | -0.008971 ± 0.007644 | [-0.021134, +0.003192] | 3/0/1 |
| reversed | 0.739323 ± 0.008557 | -0.023163 ± 0.008557 | [-0.036779, -0.009548] | 4/0/0 | 0.962106 ± 0.011935 | -0.014944 ± 0.011935 | [-0.033936, +0.004048] | 4/0/0 |
| random_s0 | 0.737218 ± 0.011736 | -0.025269 ± 0.011736 | [-0.043943, -0.006595] | 4/0/0 | 0.957908 ± 0.016176 | -0.019141 ± 0.016176 | [-0.044881, +0.006599] | 3/0/1 |
| random_s1 | 0.732491 ± 0.017602 | -0.029996 ± 0.017602 | [-0.058004, -0.001987] | 4/0/0 | 0.956425 ± 0.017666 | -0.020625 ± 0.017666 | [-0.048735, +0.007486] | 3/0/1 |
| random_s2 | 0.733919 ± 0.020174 | -0.028567 ± 0.020174 | [-0.060668, +0.003533] | 4/0/0 | 0.954979 ± 0.020453 | -0.022070 ± 0.020453 | [-0.054615, +0.010475] | 3/0/1 |
| misspecified-1 | 0.729942 ± 0.012893 | -0.032544 ± 0.012893 | [-0.053060, -0.012028] | 4/0/0 | 0.950223 ± 0.009477 | -0.026826 ± 0.009477 | [-0.041906, -0.011746] | 4/0/0 |

Persistence renal RMSE is 0.762487 on A-test and 0.977049 on B, with the same prediction in every seed; it is read from `results/v4/per_organ_v4.json`, which matches the frozen paper copy. Every arm's four-seed mean is lower than persistence on both holdouts. Every A-test seed improves, while dense and each random draw have one B seed above persistence; the other arms improve in all four B seeds. Thus the shared-input series does not reproduce the earlier mean renal deficit to persistence, but a favorable mean does not guarantee improvement for every seed or clinical subgroup. Differences and intervals here describe training variation against a deterministic baseline.

**Table 14. v5 E4 new budget records: three models × two caps × four seeds**

| ID | Model | Cap | Seed | Status | Epochs done | Best epoch | Parameters | A-val RMSE | A-test RMSE | B RMSE | Early stop |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B01 | none | 70 | 0 | complete | 64 | 56 | 778384 | 0.759268 | 0.750846 | 0.808269 | yes |
| B02 | none | 70 | 1 | complete | 70 | 64 | 778384 | 0.756418 | 0.746152 | 0.804912 | no |
| B03 | none | 70 | 2 | complete | 70 | 64 | 778384 | 0.760550 | 0.749517 | 0.807729 | no |
| B04 | none | 70 | 3 | complete | 70 | 67 | 778384 | 0.760086 | 0.751714 | 0.806951 | no |
| B05 | none | 105 | 0 | complete | 89 | 81 | 778384 | 0.757105 | 0.754317 | 0.815373 | yes |
| B06 | none | 105 | 1 | complete | 63 | 55 | 778384 | 0.759773 | 0.754844 | 0.807279 | yes |
| B07 | none | 105 | 2 | complete | 85 | 77 | 778384 | 0.758224 | 0.756660 | 0.814665 | yes |
| B08 | none | 105 | 3 | complete | 68 | 60 | 778384 | 0.760405 | 0.757294 | 0.812726 | yes |
| B09 | admissible | 70 | 0 | complete | 64 | 56 | 930464 | 0.762688 | 0.756135 | 0.814069 | yes |
| B10 | admissible | 70 | 1 | complete | 49 | 41 | 930464 | 0.768093 | 0.761137 | 0.814963 | yes |
| B11 | admissible | 70 | 2 | complete | 59 | 51 | 930464 | 0.764999 | 0.756111 | 0.815780 | yes |
| B12 | admissible | 70 | 3 | complete | 56 | 48 | 930464 | 0.763723 | 0.757304 | 0.814814 | yes |
| B13 | admissible | 105 | 0 | complete | 56 | 48 | 930464 | 0.769721 | 0.763470 | 0.822750 | yes |
| B14 | admissible | 105 | 1 | complete | 51 | 43 | 930464 | 0.766536 | 0.760420 | 0.818452 | yes |
| B15 | admissible | 105 | 2 | complete | 50 | 42 | 930464 | 0.769118 | 0.760375 | 0.816884 | yes |
| B16 | admissible | 105 | 3 | complete | 52 | 44 | 930464 | 0.767965 | 0.760420 | 0.819879 | yes |
| B17 | grud | 70 | 0 | complete | 34 | 26 | 449568 | 0.754310 | 0.747948 | 0.806002 | yes |
| B18 | grud | 70 | 1 | complete | 30 | 22 | 449568 | 0.754945 | 0.748006 | 0.809713 | yes |
| B19 | grud | 70 | 2 | complete | 35 | 27 | 449568 | 0.754023 | 0.750264 | 0.809005 | yes |
| B20 | grud | 70 | 3 | complete | 38 | 30 | 449568 | 0.755514 | 0.749355 | 0.813533 | yes |
| B21 | grud | 105 | 0 | complete | 22 | 14 | 449568 | 0.756672 | 0.748813 | 0.803330 | yes |
| B22 | grud | 105 | 1 | complete | 30 | 22 | 449568 | 0.755196 | 0.748487 | 0.810387 | yes |
| B23 | grud | 105 | 2 | complete | 32 | 24 | 449568 | 0.754411 | 0.750411 | 0.807346 | yes |
| B24 | grud | 105 | 3 | complete | 26 | 18 | 449568 | 0.756488 | 0.748841 | 0.806405 | yes |

All 24 longer-budget fits completed with finite holdout predictions. The no-edge and admissible models use the v5 shared-input selection; GRU-D keeps its frozen v4 learning rate 0.000500 and large width. Each is a fresh fit with cosine period equal to its 70- or 105-epoch cap, so these runs change the learning-rate schedule as well as available epochs. Early stopping uses A-validation only, patience eight and improvement threshold 0.000100. A best epoch below the cap is not by itself an early-stop event: the recorded curve must exhaust patience; this table uses that criterion and checks it against completed epochs.

**Table 15. v5 E4 means and convergence; epoch lists follow seed order 0, 1, 2, 3**

| Model | Cap | A-test mean ± SD | B mean ± SD | Best epochs | Completed epochs | Early stops | Reference origin |
| --- | --- | --- | --- | --- | --- | --- | --- |
| none | 35 | 0.755929 ± 0.001613 | 0.808817 ± 0.001928 | 35, 34, 34, 34 | 35, 35, 35, 35 | 0/4 | v5 shared-input arms |
| none | 70 | 0.749557 ± 0.002443 | 0.806965 ± 0.001472 | 56, 64, 64, 67 | 64, 70, 70, 70 | 1/4 | v5 fresh budget fits |
| none | 105 | 0.755779 ± 0.001424 | 0.812511 ± 0.003663 | 81, 55, 77, 60 | 89, 63, 85, 68 | 4/4 | v5 fresh budget fits |
| admissible | 35 | 0.755070 ± 0.002692 | 0.809268 ± 0.001624 | 35, 34, 34, 34 | 35, 35, 35, 35 | 0/4 | v5 shared-input arms |
| admissible | 70 | 0.757671 ± 0.002376 | 0.814907 ± 0.000701 | 56, 41, 51, 48 | 64, 49, 59, 56 | 4/4 | v5 fresh budget fits |
| admissible | 105 | 0.761171 ± 0.001533 | 0.819491 ± 0.002493 | 48, 43, 42, 44 | 56, 51, 50, 52 | 4/4 | v5 fresh budget fits |
| grud | 35 | 0.745811 ± 0.000489 | 0.805874 ± 0.000886 | 33, 32, 31, 33 | 35, 35, 35, 35 | 0/4 | frozen v4 selected GRU-D |
| grud | 70 | 0.748893 ± 0.001121 | 0.809563 ± 0.003097 | 26, 22, 27, 30 | 34, 30, 35, 38 | 4/4 | v5 fresh budget fits |
| grud | 105 | 0.749138 ± 0.000864 | 0.806867 ± 0.002906 | 14, 22, 24, 18 | 22, 30, 32, 26 | 4/4 | v5 fresh budget fits |

The no-edge model at cap 70 has A-test/B means 0.749557/0.806965, compared with 0.755929/0.808817 at 35; its cap-105 means return to 0.755779/0.812511. Admissible means rise to 0.757671/0.814907 at 70 and 0.761171/0.819491 at 105. GRU-D means are 0.745811/0.805874 at frozen 35, 0.748893/0.809563 at 70 and 0.749138/0.806867 at 105. Three no-edge cap-70 fits reach the cap; every other new budget fit stops early. The JSON retains the best-epoch frequency distributions and per-seed stopping flags. Both longer caps are reported without selecting between them on B.

**Table 16. v5 E4 longer-cap minus same-model 35-epoch reference**

| Model | Longer cap | Split | Δ mean ± SD | 95% paired t CI | Signs −/0/+ |
| --- | --- | --- | --- | --- | --- |
| none | 70 | A_test | -0.006372 ± 0.002210 | [-0.009888, -0.002855] | 4/0/0 |
| none | 70 | B | -0.001852 ± 0.001201 | [-0.003763, +0.000060] | 4/0/0 |
| none | 105 | A_test | -0.000150 ± 0.001150 | [-0.001980, +0.001680] | 2/0/2 |
| none | 105 | B | +0.003694 ± 0.002327 | [-0.000009, +0.007397] | 0/0/4 |
| admissible | 70 | A_test | +0.002601 ± 0.003693 | [-0.003274, +0.008477] | 1/0/3 |
| admissible | 70 | B | +0.005638 ± 0.002021 | [+0.002422, +0.008854] | 0/0/4 |
| admissible | 105 | A_test | +0.006101 ± 0.002211 | [+0.002583, +0.009619] | 0/0/4 |
| admissible | 105 | B | +0.010223 ± 0.002308 | [+0.006550, +0.013895] | 0/0/4 |
| grud | 70 | A_test | +0.003083 ± 0.001289 | [+0.001032, +0.005133] | 0/0/4 |
| grud | 70 | B | +0.003689 ± 0.002363 | [-0.000071, +0.007449] | 0/0/4 |
| grud | 105 | A_test | +0.003328 ± 0.000966 | [+0.001791, +0.004864] | 0/0/4 |
| grud | 105 | B | +0.000993 ± 0.003107 | [-0.003951, +0.005936] | 2/0/2 |

The no-edge cap-70 schedule improves A-test in all four seeds, with mean change −0.006372 (CI [−0.009888, −0.002855]); its B change is −0.001852 (CI [−0.003763, +0.000060]), also negative in all seeds. At cap 105, its A-test change is near zero and its B change is positive in every seed, with an interval that narrowly crosses zero. Admissible B error increases in every seed at both caps, and GRU-D A-test error increases in every seed. The longer schedules therefore do not yield a monotonic improvement with nominal budget. These paired changes compare fresh schedules, and the GRU-D 35-epoch input remains a frozen v4 reference.

**Table 17. v5 E4 organ GRU minus GRU-D at each common budget**

| Organ model | Cap | Split | Deficit mean ± SD | 95% paired t CI | Signs −/0/+ |
| --- | --- | --- | --- | --- | --- |
| none | 35 | A_test | +0.010118 ± 0.001803 | [+0.007249, +0.012987] | 0/0/4 |
| none | 35 | B | +0.002943 ± 0.001659 | [+0.000302, +0.005583] | 0/0/4 |
| none | 70 | A_test | +0.000664 ± 0.002323 | [-0.003033, +0.004361] | 2/0/2 |
| none | 70 | B | -0.002598 ± 0.003922 | [-0.008838, +0.003643] | 3/0/1 |
| none | 105 | A_test | +0.006641 ± 0.001266 | [+0.004626, +0.008656] | 0/0/4 |
| none | 105 | B | +0.005644 ± 0.006346 | [-0.004454, +0.015741] | 1/0/3 |
| admissible | 35 | A_test | +0.009260 ± 0.002502 | [+0.005279, +0.013240] | 0/0/4 |
| admissible | 35 | B | +0.003394 ± 0.002438 | [-0.000486, +0.007273] | 0/0/4 |
| admissible | 70 | A_test | +0.008778 ± 0.003086 | [+0.003868, +0.013689] | 0/0/4 |
| admissible | 70 | B | +0.005343 ± 0.002943 | [+0.000660, +0.010027] | 0/0/4 |
| admissible | 105 | A_test | +0.012033 ± 0.001948 | [+0.008934, +0.015133] | 0/0/4 |
| admissible | 105 | B | +0.012624 ± 0.005073 | [+0.004551, +0.020697] | 0/0/4 |

The no-edge A-test deficit falls from +0.010118 at 35 to +0.000664 at 70, whose interval includes zero; at 105 it is +0.006641. On B, no-edge minus GRU-D is +0.002943, −0.002598 and +0.005644 at the three caps, with both longer-cap intervals including zero. Admissible remains higher-error than GRU-D in every matched seed on both holdouts at every budget, and its B deficit grows from +0.003394 to +0.005343 to +0.012624. The organ model in E4 is the shared-input GRU architecture; no state-space-model budget experiment is available here. Frozen-v4 tuning and the changed cosine schedule limit interpretation of cross-series differences.

**Table 18. v5 E4 change in organ-model deficit relative to 35: paired difference of differences**

| Organ model | Cap | Split | Δ deficit mean ± SD | 95% paired t CI | Signs −/0/+ |
| --- | --- | --- | --- | --- | --- |
| none | 70 | A_test | -0.009454 ± 0.002501 | [-0.013434, -0.005474] | 4/0/0 |
| none | 70 | B | -0.005540 ± 0.003421 | [-0.010985, -0.000096] | 4/0/0 |
| none | 105 | A_test | -0.003477 ± 0.001894 | [-0.006491, -0.000464] | 4/0/0 |
| none | 105 | B | +0.002701 ± 0.005055 | [-0.005343, +0.010745] | 1/0/3 |
| admissible | 70 | A_test | -0.000481 ± 0.004002 | [-0.006850, +0.005887] | 2/0/2 |
| admissible | 70 | B | +0.001950 ± 0.000908 | [+0.000505, +0.003394] | 0/0/4 |
| admissible | 105 | A_test | +0.002774 ± 0.002327 | [-0.000929, +0.006476] | 0/0/4 |
| admissible | 105 | B | +0.009230 ± 0.005043 | [+0.001206, +0.017254] | 0/0/4 |

For each seed this table subtracts the 35-epoch organ-minus-GRU-D difference from the longer-cap difference; negative values mean that the organ-model deficit narrows. At cap 70, the no-edge deficit narrows by −0.009454 on A-test (CI [−0.013434, −0.005474]) and −0.005540 on B (CI [−0.010985, −0.000096]), with four negative differences in each case. The admissible B deficit instead widens by +0.001950 at 70 and +0.009230 at 105, with four positive differences and intervals excluding zero. This supports budget sensitivity of the no-edge comparison, while the admissible model's deficit is not removed by these schedules; it does not isolate a pure effect of elapsed training time.

**Table 19. v5 selected-none determinism condition and frozen-series continuity**

| Seed | v5 none ID | renal diagnostic shared ID | shared-edge diagnostic none ID | v5 exact-reproduction test | renal diagnostic–shared-edge diagnostic max abs metric Δ | Compared scalars |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | A01 | D17s0 | D20s0 | config differs | 0.000000 | 13 |
| 1 | A02 | D17s1 | D20s1 | config differs | 0.000000 | 13 |
| 2 | A03 | D17s2 | D20s2 | config differs | 0.000000 | 13 |
| 3 | A04 | D17s3 | D20s3 | config differs | 0.000000 | 13 |

The selected v5 `none` configuration differs: it uses learning rate 0.001000, while renal diagnostic shared and shared-edge diagnostic `none` use 0.000500; both widths are large. The selected-arm determinism result is therefore “config differs,” not a failure to reproduce an identical configuration. renal diagnostic and shared-edge diagnostic agree exactly for every seed over validation RMSE, A-test/B pooled RMSE and mean absolute error (MAE), and all A-test/B organ RMSEs: maximum absolute recorded-metric difference 0.000000. No new inference or checkpoint tensor comparison was performed, and matching summary metrics alone does not establish prediction-array identity.

**Table 20. v5 companion continuity check at the old configuration, seed 0**

| v5 grid ID | shared-edge diagnostic ID | Configuration | Compared RMSE scalars | Maximum absolute RMSE difference |
| --- | --- | --- | --- | --- |
| G01 | D20s0 | lr0.0005_large | 11 | 0.000000 |

The unselected v5 grid cell at the old learning rate and width reproduces shared-edge diagnostic seed-0 validation, A-test/B pooled RMSE and all A-test/B organ RMSEs exactly, with maximum absolute difference 0.000000. This companion result checks continuity at an actually matching configuration, but only seed 0 was run in that grid cell; it does not turn the different selected v5 learning rate into an all-seed determinism comparison. Source-file SHA-256 hashes and the exact metric fields used are retained in the JSON and receipt.

The reading contains the complete requested v5 inventory and all calculated paired summaries. It is an engineering and evidence reading by the calculation author, not independent scientific review. The receipt records commands, exit codes, input run hashes and UTC times. Scientific evidence freezes and review eligibility are unchanged; the owner's current delivery-first paper direction was followed without adding editorial reader or style gates.
