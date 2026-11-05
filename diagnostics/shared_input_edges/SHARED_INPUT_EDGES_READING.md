# post-hoc shared-input edge-ablation reading

Root mean squared error (RMSE) pools observed squared errors over stays, forecast hours, and variables before taking the square root. The pooled score uses all organs; each organ score uses its own observed-entry denominator. A means A-test and B means the external hospital. Units are A-train standard deviations. Scores cover the complete forecast horizon, not only its last hour. Seed means average the per-run RMSEs; they do not average organ RMSEs.

This reading uses all 24 full runs: six variants with paired seeds 0–3. Every run is `complete` and has 35 completed epochs. No run is excluded. Each node receives all 16 variables. The run table reports each score as A / B. Tables display metric values to six decimals; decisions and the companion JSON use unrounded stored values. Integer counts remain integers.

## Source fields and calculation policy

The run fields are `variant`, `seed`, `status`, `epochs_completed`, and `n_params`; pooled RMSE is `<split>.pooled_masked_RMSE`; organ RMSE is `<split>.organs.<organ>.RMSE`, for cardiovascular, pulmonary, renal, and metabolic. Training-device metadata are top-level `device` and `threads`, while software metadata are in `runtime`. Every requested metric field is present. No error archive was read and no metric was recomputed using `renal_protocol.metrics()`. The formulas were read from that function; only differences, across-seed summaries, ordering, and comparisons were computed here.

The JSON stores each observed value with its file identifier and exact field, each derived value with its formula and input references, and the displayed table cells with their JSON references. Its source manifest and distribution inventory identify the exact input bytes by SHA256.

## All saved runs

| Variant | Seed | Status | Epochs completed | Parameters | Pooled A / B | Cardiovascular A / B | Pulmonary A / B | Renal A / B | Metabolic A / B |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| none | 0 | complete | 35 | 778384 | 0.756991 / 0.811263 | 0.696719 / 0.800309 | 0.831976 / 0.813975 | 0.714097 / 0.941480 | 0.815623 / 0.830429 |
| none | 1 | complete | 35 | 778384 | 0.756987 / 0.808053 | 0.694947 / 0.795241 | 0.833757 / 0.814245 | 0.712924 / 0.941381 | 0.817905 / 0.827041 |
| none | 2 | complete | 35 | 778384 | 0.759251 / 0.810247 | 0.695585 / 0.797213 | 0.839006 / 0.815106 | 0.715663 / 0.944142 | 0.817470 / 0.833836 |
| none | 3 | complete | 35 | 778384 | 0.758646 / 0.811004 | 0.696028 / 0.798686 | 0.835830 / 0.815224 | 0.705326 / 0.931436 | 0.823616 / 0.836131 |
| admissible | 0 | complete | 35 | 930464 | 0.756828 / 0.811970 | 0.695188 / 0.797374 | 0.828777 / 0.813682 | 0.749974 / 0.989999 | 0.819960 / 0.839887 |
| admissible | 1 | complete | 35 | 930464 | 0.756819 / 0.810782 | 0.695116 / 0.796676 | 0.830134 / 0.814642 | 0.724261 / 0.955237 | 0.823919 / 0.839831 |
| admissible | 2 | complete | 35 | 930464 | 0.756173 / 0.809454 | 0.694513 / 0.795072 | 0.828618 / 0.813871 | 0.730564 / 0.951996 | 0.823713 / 0.839016 |
| admissible | 3 | complete | 35 | 930464 | 0.755182 / 0.809805 | 0.694597 / 0.795604 | 0.826599 / 0.813877 | 0.730240 / 0.957584 | 0.821109 / 0.837872 |
| dense | 0 | complete | 35 | 1006504 | 0.754933 / 0.809279 | 0.694722 / 0.794717 | 0.826868 / 0.813336 | 0.724348 / 0.958634 | 0.819314 / 0.838869 |
| dense | 1 | complete | 35 | 1006504 | 0.756020 / 0.811154 | 0.694785 / 0.795900 | 0.826144 / 0.813259 | 0.748262 / 0.986158 | 0.823534 / 0.842373 |
| dense | 2 | complete | 35 | 1006504 | 0.756063 / 0.812571 | 0.694897 / 0.796352 | 0.825291 / 0.815913 | 0.762406 / 0.989126 | 0.821604 / 0.845200 |
| dense | 3 | complete | 35 | 1006504 | 0.754105 / 0.809889 | 0.695249 / 0.796128 | 0.826086 / 0.813173 | 0.729438 / 0.968356 | 0.810516 / 0.834731 |
| reversed | 0 | complete | 35 | 930464 | 0.756761 / 0.811726 | 0.695305 / 0.796314 | 0.824962 / 0.812431 | 0.749000 / 0.984656 | 0.831382 / 0.848035 |
| reversed | 1 | complete | 35 | 930464 | 0.755699 / 0.811519 | 0.694903 / 0.797075 | 0.827335 / 0.813625 | 0.736427 / 0.974202 | 0.820082 / 0.841927 |
| reversed | 2 | complete | 35 | 930464 | 0.755234 / 0.812285 | 0.694731 / 0.797079 | 0.823649 / 0.813329 | 0.764437 / 0.993114 | 0.819537 / 0.844393 |
| reversed | 3 | complete | 35 | 930464 | 0.755766 / 0.810871 | 0.694658 / 0.795598 | 0.826044 / 0.813859 | 0.754784 / 0.986652 | 0.820048 / 0.839648 |
| random | 0 | complete | 35 | 930464 | 0.754746 / 0.811150 | 0.694425 / 0.795786 | 0.823852 / 0.814170 | 0.741408 / 0.984453 | 0.823279 / 0.841028 |
| random | 1 | complete | 35 | 930464 | 0.755763 / 0.810318 | 0.695599 / 0.796419 | 0.828499 / 0.813600 | 0.737598 / 0.968904 | 0.813466 / 0.835864 |
| random | 2 | complete | 35 | 930464 | 0.753820 / 0.811113 | 0.696048 / 0.796735 | 0.821041 / 0.813665 | 0.743849 / 0.971376 | 0.816174 / 0.840667 |
| random | 3 | complete | 35 | 930464 | 0.753812 / 0.809284 | 0.695327 / 0.794930 | 0.824634 / 0.813490 | 0.744097 / 0.973253 | 0.807573 / 0.833288 |
| misspecified-1 | 0 | complete | 35 | 930464 | 0.756003 / 0.811015 | 0.695289 / 0.796886 | 0.827414 / 0.813818 | 0.742957 / 0.973727 | 0.818785 / 0.837904 |
| misspecified-1 | 1 | complete | 35 | 930464 | 0.757077 / 0.811552 | 0.695061 / 0.796605 | 0.830964 / 0.815100 | 0.734800 / 0.969601 | 0.820501 / 0.842121 |
| misspecified-1 | 2 | complete | 35 | 930464 | 0.756529 / 0.810516 | 0.695479 / 0.795596 | 0.825928 / 0.813621 | 0.746374 / 0.974914 | 0.826332 / 0.840328 |
| misspecified-1 | 3 | complete | 35 | 930464 | 0.754519 / 0.809385 | 0.694465 / 0.795306 | 0.826293 / 0.813179 | 0.744637 / 0.973609 | 0.812177 / 0.832943 |

## Pooled seed summaries and ordering

Sample standard deviation (sd) uses the number of seeds minus one in its denominator. The min–max interval and its width describe seed variation, not a confidence interval.

| Variant | Split | Mean | Sample sd | Minimum | Maximum | Span (max − min) |
| --- | --- | --- | --- | --- | --- | --- |
| none | A | 0.757969 | 0.001158 | 0.756987 | 0.759251 | 0.002265 |
| none | B | 0.810142 | 0.001458 | 0.808053 | 0.811263 | 0.003210 |
| admissible | A | 0.756250 | 0.000776 | 0.755182 | 0.756828 | 0.001646 |
| admissible | B | 0.810503 | 0.001128 | 0.809454 | 0.811970 | 0.002515 |
| dense | A | 0.755280 | 0.000942 | 0.754105 | 0.756063 | 0.001959 |
| dense | B | 0.810723 | 0.001458 | 0.809279 | 0.812571 | 0.003291 |
| reversed | A | 0.755865 | 0.000642 | 0.755234 | 0.756761 | 0.001527 |
| reversed | B | 0.811600 | 0.000584 | 0.810871 | 0.812285 | 0.001413 |
| random | A | 0.754535 | 0.000928 | 0.753812 | 0.755763 | 0.001951 |
| random | B | 0.810466 | 0.000876 | 0.809284 | 0.811150 | 0.001866 |
| misspecified-1 | A | 0.756032 | 0.001100 | 0.754519 | 0.757077 | 0.002558 |
| misspecified-1 | B | 0.810617 | 0.000924 | 0.809385 | 0.811552 | 0.002167 |

Ascending shared-input A order: **random < dense < reversed < misspecified-1 < admissible < none**. Ascending shared-input B order: **none < random < admissible < misspecified-1 < dense < reversed**. No variant is lowest on both cohorts.

For the one-sd comparison, the reference is the no-edge sample sd on each split: A **0.001158**, B **0.001458**. A variant is within this scale when the absolute difference of its seed mean from the no-edge seed mean is at most that split's no-edge sd. This is a descriptive threshold, not a significance test. All variants are not within this scale: on A, every edge variant is outside it in the direction of lower error; on B, reversed is just outside it in the direction of higher error, and the other variants are within it. Reversed's B excess over the threshold is positive at full precision, so its classification must not be inferred from rounded table entries.

| Split | Variant | Mean − none mean | None sample sd used | Absolute gap / none sd | Within one none sd? |
| --- | --- | --- | --- | --- | --- |
| A | none | +0.000000 | 0.001158 | 0.000000 | True |
| A | admissible | -0.001719 | 0.001158 | 1.483864 | False |
| A | dense | -0.002689 | 0.001158 | 2.321467 | False |
| A | reversed | -0.002104 | 0.001158 | 1.816492 | False |
| A | random | -0.003434 | 0.001158 | 2.964915 | False |
| A | misspecified-1 | -0.001937 | 0.001158 | 1.672488 | False |
| B | none | +0.000000 | 0.001458 | 0.000000 | True |
| B | admissible | +0.000361 | 0.001458 | 0.247458 | True |
| B | dense | +0.000581 | 0.001458 | 0.398884 | True |
| B | reversed | +0.001459 | 0.001458 | 1.000518 | False |
| B | random | +0.000324 | 0.001458 | 0.222557 | True |
| B | misspecified-1 | +0.000475 | 0.001458 | 0.326140 | True |

## Paired differences, variant minus no-edge

Negative differences mean lower RMSE with that variant. Signs count negative / exact zero / positive differences out of the paired seeds. The no-edge rows are the zero reference. Means are means of the unrounded paired differences.

| Split | Variant | Target | Seed 0 | Seed 1 | Seed 2 | Seed 3 | Mean | Minimum | Maximum | Signs negative / zero / positive |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | none | pooled | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | 0 / 4 / 0 out of 4 |
| A | none | cardiovascular | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | 0 / 4 / 0 out of 4 |
| A | none | pulmonary | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | 0 / 4 / 0 out of 4 |
| A | none | renal | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | 0 / 4 / 0 out of 4 |
| A | none | metabolic | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | 0 / 4 / 0 out of 4 |
| A | admissible | pooled | -0.000164 | -0.000168 | -0.003078 | -0.003465 | -0.001719 | -0.003465 | -0.000164 | 4 / 0 / 0 out of 4 |
| A | admissible | cardiovascular | -0.001531 | +0.000168 | -0.001072 | -0.001430 | -0.000966 | -0.001531 | +0.000168 | 3 / 0 / 1 out of 4 |
| A | admissible | pulmonary | -0.003199 | -0.003623 | -0.010387 | -0.009231 | -0.006610 | -0.010387 | -0.003199 | 4 / 0 / 0 out of 4 |
| A | admissible | renal | +0.035877 | +0.011337 | +0.014900 | +0.024914 | +0.021757 | +0.011337 | +0.035877 | 0 / 0 / 4 out of 4 |
| A | admissible | metabolic | +0.004337 | +0.006013 | +0.006243 | -0.002507 | +0.003522 | -0.002507 | +0.006243 | 1 / 0 / 3 out of 4 |
| A | dense | pooled | -0.002058 | -0.000966 | -0.003188 | -0.004542 | -0.002689 | -0.004542 | -0.000966 | 4 / 0 / 0 out of 4 |
| A | dense | cardiovascular | -0.001997 | -0.000163 | -0.000688 | -0.000779 | -0.000907 | -0.001997 | -0.000163 | 4 / 0 / 0 out of 4 |
| A | dense | pulmonary | -0.005109 | -0.007613 | -0.013714 | -0.009744 | -0.009045 | -0.013714 | -0.005109 | 4 / 0 / 0 out of 4 |
| A | dense | renal | +0.010251 | +0.035337 | +0.046742 | +0.024111 | +0.029111 | +0.010251 | +0.046742 | 0 / 0 / 4 out of 4 |
| A | dense | metabolic | +0.003690 | +0.005629 | +0.004133 | -0.013100 | +0.000088 | -0.013100 | +0.005629 | 1 / 0 / 3 out of 4 |
| A | reversed | pooled | -0.000230 | -0.001287 | -0.004017 | -0.002880 | -0.002104 | -0.004017 | -0.000230 | 4 / 0 / 0 out of 4 |
| A | reversed | cardiovascular | -0.001415 | -0.000044 | -0.000854 | -0.001370 | -0.000921 | -0.001415 | -0.000044 | 4 / 0 / 0 out of 4 |
| A | reversed | pulmonary | -0.007015 | -0.006422 | -0.015357 | -0.009786 | -0.009645 | -0.015357 | -0.006422 | 4 / 0 / 0 out of 4 |
| A | reversed | renal | +0.034903 | +0.023502 | +0.048773 | +0.049458 | +0.039159 | +0.023502 | +0.049458 | 0 / 0 / 4 out of 4 |
| A | reversed | metabolic | +0.015758 | +0.002177 | +0.002066 | -0.003568 | +0.004108 | -0.003568 | +0.015758 | 1 / 0 / 3 out of 4 |
| A | random | pooled | -0.002246 | -0.001224 | -0.005431 | -0.004834 | -0.003434 | -0.005431 | -0.001224 | 4 / 0 / 0 out of 4 |
| A | random | cardiovascular | -0.002295 | +0.000652 | +0.000463 | -0.000701 | -0.000470 | -0.002295 | +0.000652 | 2 / 0 / 2 out of 4 |
| A | random | pulmonary | -0.008124 | -0.005259 | -0.017964 | -0.011196 | -0.010636 | -0.017964 | -0.005259 | 4 / 0 / 0 out of 4 |
| A | random | renal | +0.027311 | +0.024674 | +0.028185 | +0.038771 | +0.029735 | +0.024674 | +0.038771 | 0 / 0 / 4 out of 4 |
| A | random | metabolic | +0.007655 | -0.004440 | -0.001296 | -0.016043 | -0.003531 | -0.016043 | +0.007655 | 3 / 0 / 1 out of 4 |
| A | misspecified-1 | pooled | -0.000989 | +0.000091 | -0.002722 | -0.004127 | -0.001937 | -0.004127 | +0.000091 | 3 / 0 / 1 out of 4 |
| A | misspecified-1 | cardiovascular | -0.001430 | +0.000114 | -0.000106 | -0.001562 | -0.000746 | -0.001562 | +0.000114 | 3 / 0 / 1 out of 4 |
| A | misspecified-1 | pulmonary | -0.004562 | -0.002793 | -0.013077 | -0.009537 | -0.007492 | -0.013077 | -0.002793 | 4 / 0 / 0 out of 4 |
| A | misspecified-1 | renal | +0.028860 | +0.021876 | +0.030711 | +0.039310 | +0.030189 | +0.021876 | +0.039310 | 0 / 0 / 4 out of 4 |
| A | misspecified-1 | metabolic | +0.003162 | +0.002596 | +0.008862 | -0.011439 | +0.000795 | -0.011439 | +0.008862 | 1 / 0 / 3 out of 4 |
| B | none | pooled | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | 0 / 4 / 0 out of 4 |
| B | none | cardiovascular | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | 0 / 4 / 0 out of 4 |
| B | none | pulmonary | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | 0 / 4 / 0 out of 4 |
| B | none | renal | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | 0 / 4 / 0 out of 4 |
| B | none | metabolic | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | 0 / 4 / 0 out of 4 |
| B | admissible | pooled | +0.000706 | +0.002729 | -0.000793 | -0.001199 | +0.000361 | -0.001199 | +0.002729 | 2 / 0 / 2 out of 4 |
| B | admissible | cardiovascular | -0.002935 | +0.001435 | -0.002141 | -0.003081 | -0.001681 | -0.003081 | +0.001435 | 3 / 0 / 1 out of 4 |
| B | admissible | pulmonary | -0.000294 | +0.000397 | -0.001234 | -0.001347 | -0.000620 | -0.001347 | +0.000397 | 3 / 0 / 1 out of 4 |
| B | admissible | renal | +0.048519 | +0.013856 | +0.007854 | +0.026148 | +0.024095 | +0.007854 | +0.048519 | 0 / 0 / 4 out of 4 |
| B | admissible | metabolic | +0.009458 | +0.012789 | +0.005180 | +0.001740 | +0.007292 | +0.001740 | +0.012789 | 0 / 0 / 4 out of 4 |
| B | dense | pooled | -0.001984 | +0.003101 | +0.002324 | -0.001115 | +0.000581 | -0.001984 | +0.003101 | 2 / 0 / 2 out of 4 |
| B | dense | cardiovascular | -0.005592 | +0.000659 | -0.000862 | -0.002558 | -0.002088 | -0.005592 | +0.000659 | 3 / 0 / 1 out of 4 |
| B | dense | pulmonary | -0.000640 | -0.000986 | +0.000807 | -0.002051 | -0.000717 | -0.002051 | +0.000807 | 3 / 0 / 1 out of 4 |
| B | dense | renal | +0.017154 | +0.044777 | +0.044985 | +0.036920 | +0.035959 | +0.017154 | +0.044985 | 0 / 0 / 4 out of 4 |
| B | dense | metabolic | +0.008439 | +0.015332 | +0.011364 | -0.001400 | +0.008434 | -0.001400 | +0.015332 | 1 / 0 / 3 out of 4 |
| B | reversed | pooled | +0.000463 | +0.003466 | +0.002038 | -0.000133 | +0.001459 | -0.000133 | +0.003466 | 1 / 0 / 3 out of 4 |
| B | reversed | cardiovascular | -0.003995 | +0.001834 | -0.000135 | -0.003088 | -0.001346 | -0.003995 | +0.001834 | 3 / 0 / 1 out of 4 |
| B | reversed | pulmonary | -0.001545 | -0.000620 | -0.001777 | -0.001364 | -0.001326 | -0.001777 | -0.000620 | 4 / 0 / 0 out of 4 |
| B | reversed | renal | +0.043176 | +0.032822 | +0.048972 | +0.055216 | +0.045046 | +0.032822 | +0.055216 | 0 / 0 / 4 out of 4 |
| B | reversed | metabolic | +0.017606 | +0.014885 | +0.010557 | +0.003516 | +0.011641 | +0.003516 | +0.017606 | 0 / 0 / 4 out of 4 |
| B | random | pooled | -0.000113 | +0.002265 | +0.000866 | -0.001720 | +0.000324 | -0.001720 | +0.002265 | 2 / 0 / 2 out of 4 |
| B | random | cardiovascular | -0.004523 | +0.001178 | -0.000478 | -0.003756 | -0.001895 | -0.004523 | +0.001178 | 3 / 0 / 1 out of 4 |
| B | random | pulmonary | +0.000194 | -0.000645 | -0.001440 | -0.001733 | -0.000906 | -0.001733 | +0.000194 | 3 / 0 / 1 out of 4 |
| B | random | renal | +0.042973 | +0.027523 | +0.027234 | +0.041817 | +0.034887 | +0.027234 | +0.042973 | 0 / 0 / 4 out of 4 |
| B | random | metabolic | +0.010599 | +0.008823 | +0.006831 | -0.002843 | +0.005852 | -0.002843 | +0.010599 | 1 / 0 / 3 out of 4 |
| B | misspecified-1 | pooled | -0.000248 | +0.003499 | +0.000270 | -0.001619 | +0.000475 | -0.001619 | +0.003499 | 2 / 0 / 2 out of 4 |
| B | misspecified-1 | cardiovascular | -0.003423 | +0.001364 | -0.001617 | -0.003380 | -0.001764 | -0.003423 | +0.001364 | 3 / 0 / 1 out of 4 |
| B | misspecified-1 | pulmonary | -0.000158 | +0.000855 | -0.001485 | -0.002044 | -0.000708 | -0.002044 | +0.000855 | 3 / 0 / 1 out of 4 |
| B | misspecified-1 | renal | +0.032247 | +0.028220 | +0.030772 | +0.042173 | +0.033353 | +0.028220 | +0.042173 | 0 / 0 / 4 out of 4 |
| B | misspecified-1 | metabolic | +0.007475 | +0.015080 | +0.006492 | -0.003188 | +0.006465 | -0.003188 | +0.015080 | 1 / 0 / 3 out of 4 |

## Frozen partitioned backbone comparison

The partitioned gated recurrent unit (GRU) backbone is `table.physiograph_gru` in the frozen `variant_ablation_v4.json`. The side-by-side table uses its recorded `<variant>.<split>.mean` fields, without recomputing or reranking the shared backbone against other model series. Frozen means are shown as recorded; this table does not compare either series with headline baselines.

| Variant | Shared A mean | Partitioned GRU A recorded mean | Shared B mean | Partitioned GRU B recorded mean |
| --- | --- | --- | --- | --- |
| none | 0.757969 | 0.772360 | 0.810142 | 0.818781 |
| admissible | 0.756250 | 0.770165 | 0.810503 | 0.817699 |
| dense | 0.755280 | 0.770865 | 0.810723 | 0.818773 |
| reversed | 0.755865 | 0.772530 | 0.811600 | 0.820223 |
| random | 0.754535 | 0.771136 | 0.810466 | 0.819330 |
| misspecified-1 | 0.756032 | 0.772406 | 0.810617 | 0.819877 |

Ascending partitioned GRU A order: **admissible < dense < random < none < misspecified-1 < reversed**. Ascending partitioned GRU B order: **admissible < dense < none < random < misspecified-1 < reversed**. Admissible is lowest on both. Every partitioned GRU variant's mean is within one no-edge sample sd of no-edge on each split, using the frozen no-edge `sd_sample` fields: A **0.003304**, B **0.002618**. Admissible minus no-edge is **-0.002194** on A and **-0.001082** on B, so both nominal improvements are smaller than those respective sds. The same frozen file's `table.physiograph` records no-edge as the lowest state-space model (SSM) variant on both cohorts; that is a separate backbone statement.

For the card's contradiction criterion, the shared-input mean differences and thresholds are in the one-sd table above. All edge variants improve A by more than its no-edge sd, but every edge variant has a higher B mean than no-edge. Consequently no variant has an improvement greater than one no-edge sd on both cohorts. This is consistent with C2 under the specified criterion; it does not establish an edge prior's advantage and does not authorize a ledger change by this worker.

## Renal RMSE against frozen persistence

Frozen renal persistence is **0.762487** on A and **0.977049** on B, from `selected_seed_summary.persistence.<split>.renal.mean` in `results/v4/per_organ_v4.json`. The repeated `per_seed` values are identical and do not represent independent persistence fits. A negative difference is better than persistence; a positive difference is worse. This is the requested organ control, with no ranking against other baseline series.

| Variant | Seed | A renal RMSE | A − persistence | A relation | B renal RMSE | B − persistence | B relation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| none | 0 | 0.714097 | -0.048390 | better | 0.941480 | -0.035570 | better |
| none | 1 | 0.712924 | -0.049562 | better | 0.941381 | -0.035669 | better |
| none | 2 | 0.715663 | -0.046823 | better | 0.944142 | -0.032908 | better |
| none | 3 | 0.705326 | -0.057160 | better | 0.931436 | -0.045613 | better |
| admissible | 0 | 0.749974 | -0.012512 | better | 0.989999 | +0.012950 | worse |
| admissible | 1 | 0.724261 | -0.038226 | better | 0.955237 | -0.021812 | better |
| admissible | 2 | 0.730564 | -0.031923 | better | 0.951996 | -0.025053 | better |
| admissible | 3 | 0.730240 | -0.032246 | better | 0.957584 | -0.019465 | better |
| dense | 0 | 0.724348 | -0.038138 | better | 0.958634 | -0.018415 | better |
| dense | 1 | 0.748262 | -0.014225 | better | 0.986158 | +0.009108 | worse |
| dense | 2 | 0.762406 | -0.000081 | better | 0.989126 | +0.012077 | worse |
| dense | 3 | 0.729438 | -0.033049 | better | 0.968356 | -0.008694 | better |
| reversed | 0 | 0.749000 | -0.013486 | better | 0.984656 | +0.007606 | worse |
| reversed | 1 | 0.736427 | -0.026060 | better | 0.974202 | -0.002847 | better |
| reversed | 2 | 0.764437 | +0.001950 | worse | 0.993114 | +0.016064 | worse |
| reversed | 3 | 0.754784 | -0.007702 | better | 0.986652 | +0.009602 | worse |
| random | 0 | 0.741408 | -0.021078 | better | 0.984453 | +0.007403 | worse |
| random | 1 | 0.737598 | -0.024888 | better | 0.968904 | -0.008145 | better |
| random | 2 | 0.743849 | -0.018638 | better | 0.971376 | -0.005674 | better |
| random | 3 | 0.744097 | -0.018389 | better | 0.973253 | -0.003796 | better |
| misspecified-1 | 0 | 0.742957 | -0.019530 | better | 0.973727 | -0.003323 | better |
| misspecified-1 | 1 | 0.734800 | -0.027687 | better | 0.969601 | -0.007449 | better |
| misspecified-1 | 2 | 0.746374 | -0.016112 | better | 0.974914 | -0.002136 | better |
| misspecified-1 | 3 | 0.744637 | -0.017850 | better | 0.973609 | -0.003440 | better |

## renal diagnostic determinism comparison

Each edge ablation no-edge seed is paired with the same renal diagnostic shared-input seed. The comparison uses exact equality of the parsed, unrounded JSON values for pooled RMSE and every organ RMSE. The maximum is over the named metrics within a split, and the across-seed maximum is **0.000000** on A and **0.000000** on B. Parameter counts match exactly. This establishes equality of the requested recorded metrics, not independent verification of checkpoint tensors or per-stay error archives.

| Seed | A pooled abs Δ | A max organ abs Δ | A max all abs Δ | B pooled abs Δ | B max organ abs Δ | B max all abs Δ | edge ablation parameters | renal diagnostic parameters | Parameter Δ | edge ablation device | renal diagnostic device |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 778384 | 778384 | 0 | cuda | not recorded |
| 1 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 778384 | 778384 | 0 | cuda | not recorded |
| 2 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 778384 | 778384 | 0 | cuda | not recorded |
| 3 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 778384 | 778384 | 0 | cuda | not recorded |

All edge ablation runs explicitly record `device: cuda` and `threads: 4`. renal diagnostic's run files omit the actual device and thread-count fields. The `runtime` dictionaries match exactly for each paired seed; `runtime.torch` records the CUDA-enabled build `2.6.0+cu124` in both series, which alone does not identify the device used by renal diagnostic. renal diagnostic's actual device therefore remains unrecorded by the requested run-file evidence. The reproduction note's planned CUDA execution is not treated as observed runtime metadata.

The capacity caveat inherited from renal diagnostic is visible in the counts: the frozen partitioned no-edge GRU has **759952** parameters, while the shared-input no-edge GRU has **778384**, a difference of **18432**. Parameter counts also vary within the shared-input study, as shown in the run table. These comparisons do not separate graph structure from parameter capacity.

## Plain-language interpretation

This post-hoc control holds shared input access fixed: every organ node receives all 16 dynamic variables and their masks, while the edge set changes. For these saved fits, every edge variant has lower mean pooled error on A than no-edge, but no-edge has the lowest mean on B; no edge variant is lowest on both cohorts. Renal error is higher than no-edge for every edge variant in every paired seed on both cohorts, so the pooled ordering does not establish uniform organ improvement. The configuration was selected on the partitioned backbone and reused without retuning; there are only four paired seeds and no significance test. The capacity caveat from renal diagnostic remains: widening input projections also changes capacity, and edge variants here allocate different parameter counts. Thus the comparison does not isolate a physiological graph prior from input access, projection capacity, message capacity, or optimization, and it does not establish clinical benefit or a causal effect. The frozen partitioned GRU comparison shows that admissible is nominally lowest on both cohorts, within the no-edge seed standard deviation; the frozen SSM table also has no-edge lowest on both. The shared-input result has a different ordering but does not meet the descriptive comparison criterion: no variant beats no-edge on both cohorts by more than the corresponding no-edge seed standard deviation. These descriptive comparisons do not establish a physiological or causal advantage.
