# CinC-2012 cohort report

Frozen build report. Input fingerprints identify the original files; current
distribution fingerprints are recorded separately in `manifests/distribution.json`.

Built from the maintainer-supplied archives, offline, on CPU. All 8,000 records are retained; forecasting eligibility is separate from cohort inclusion. No forecasting models were fitted and no model-ranking claim is made here.

## Counts and temporal protocol

| Partition | Retained | Eligible at C+K=24 | Ineligible |
|---|---:|---:|---:|
| A train | 3400 | 3390 | 10 |
| A validation | 600 | 599 | 1 |
| B test | 4000 | 3993 | 7 |
| Total | 8000 | 7982 | 18 |

A and B each contain 4,000 distinct stays and their RecordID sets are disjoint. Sorted archive-member filenames determine row order. With numpy.random.default_rng(0).permutation(4000), the first 600 indices are validation and the remaining 3,400 are training. This retains the 2019 RNG and seed rule while honoring this card's 85/15 split, rather than the 2019 70/15/15 split. B is never used for fitting normalization. These 2012 challenge sets are not asserted to be different hospitals; the unchanged loader's hospital=0/1 field identifies set A/B only.

Each hour h=0,...,47 contains the arithmetic mean of valid observations in [h,h+1). There is no interpolation or forward fill. Multiple observations, including duplicate timestamps, receive equal weight. For each pressure variable in each hour, invasive observations are averaged if present; otherwise noninvasive observations are averaged. The two measurement methods are never pooled within an hour. Missing values are zero with mask=0; true zero readings retain mask=1. Nonfinite and negative readings are invalid under the 2012 documentation's nonnegative-value rule. No other outlier cleaning or unit inference from individual readings is applied.

Length is the last hour with any valid time-series observation plus one, using both mapped and unselected source channels, including later Weight observations. Admission descriptors do not establish temporal coverage; a descriptor-only stay has length zero. This follows the source timeline rather than truncating it to the selected variables, consistent with the 2019 use of source rows for length. Thus length>=24 is a recorded-coverage criterion, not a clinical length-of-stay estimate. An observation at exactly 48:00 is excluded, consistent with the specified half-open grid.

A/B contain 4/7 stays with no mapped observations, including 3/7 descriptor-only stays; lengths range 0–48 / 0–48. Source-timeline length differs from mapped-variable length in 56/52 stays. Both are in the NPZ and COHORT_MANIFEST.tsv for audit. Two stays become 24-hour eligible solely through unselected channels: A RecordID 132988 has mapped length 23, and B RecordID 150611 has mapped length 16. The loader retains these under the specified length rule.

Among length-eligible stays, A/B have 9/14 with no observations in hours 0–11 and 16/22 with no observations in hours 12–23. The unchanged loader uses only length eligibility; these stays are retained.

## Observation rates

The main denominator is 4,000 x 48 = 192,000 padded stay-hours per set and feature. 'Within length' uses the sum of source-timeline lengths (including empty hours before the last observed hour). '24h eligible' uses eligible stays x 24. These are measured hourly cells after pressure fallback, not raw sample counts.

| Feature | A observed hours | A / 192000 | B observed hours | B / 192000 | A within length | B within length | A 24h eligible | B 24h eligible | A/B stays ever observed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| HR | 172883 | 90.0432% | 172985 | 90.0964% | 90.7384% | 90.7267% | 89.1504% | 89.1790% | 3937/3935 |
| SBP | 170153 | 88.6214% | 170436 | 88.7687% | 89.3056% | 89.3898% | 88.1528% | 88.2158% | 3937/3935 |
| MAP | 168832 | 87.9333% | 169045 | 88.0443% | 88.6122% | 88.6603% | 87.4593% | 87.5052% | 3937/3935 |
| DBP | 170135 | 88.6120% | 170407 | 88.7536% | 89.2961% | 89.3746% | 88.1434% | 88.2033% | 3937/3935 |
| O2Sat | 7890 | 4.1094% | 7338 | 3.8219% | 4.1411% | 3.8486% | 5.0963% | 4.8533% | 1792/1753 |
| Resp | 45855 | 23.8828% | 47258 | 24.6135% | 24.0672% | 24.7858% | 24.1341% | 24.7850% | 1101/1127 |
| FiO2 | 30729 | 16.0047% | 30024 | 15.6375% | 16.1283% | 15.7469% | 18.3254% | 17.9189% | 2717/2702 |
| PaCO2 | 22413 | 11.6734% | 21980 | 11.4479% | 11.7636% | 11.5280% | 15.2565% | 14.9073% | 3023/3012 |
| Creatinine | 13953 | 7.2672% | 13938 | 7.2594% | 7.3233% | 7.3102% | 8.6498% | 8.6631% | 3936/3944 |
| BUN | 13887 | 7.2328% | 13865 | 7.2214% | 7.2887% | 7.2719% | 8.6143% | 8.6161% | 3936/3944 |
| Potassium | 14406 | 7.5031% | 14631 | 7.6203% | 7.5611% | 7.6736% | 8.6248% | 8.7904% | 3904/3927 |
| Lactate | 7831 | 4.0786% | 8218 | 4.2802% | 4.1101% | 4.3102% | 5.8379% | 5.9709% | 2183/2215 |
| Glucose | 12988 | 6.7646% | 13122 | 6.8344% | 6.8168% | 6.8822% | 7.8706% | 7.9639% | 3887/3912 |
| HCO3 | 13582 | 7.0740% | 13583 | 7.0745% | 7.1286% | 7.1240% | 8.4200% | 8.4189% | 3924/3939 |
| WBC | 12849 | 6.6922% | 13038 | 6.7906% | 6.7439% | 6.8381% | 8.1077% | 8.1445% | 3927/3934 |
| Temp | 71199 | 37.0828% | 70010 | 36.4635% | 37.3691% | 36.7187% | 39.7614% | 38.9765% | 3936/3935 |

All 16 mapped variables are present in both sets. Sparse SaO2 is retained as specified; no substitute channel is introduced.

## Unit decisions and evidence limits

Unit descriptions were checked against the local GraFITi/tsdm PhysioNet dataset modules listed in BUILD_SUMMARY.json, with their hashes, and against numerical distributions in the frozen 2019 NPZ. These are local secondary transcriptions, not a fresh primary-source verification. Network access was prohibited; the official PhysioNet pages were not fetched. The two conflicting declarations below remain explicitly unresolved. The effective scales describe compatibility with the frozen NPZ; numerical agreement alone does not prove physical units.

| Target feature | 2012 source(s) | 2012 declared unit | 2019 locally declared unit | Stored numerical convention | Decision |
|---|---|---|---|---|---|
| HR | HR | beats/min | beats/min | beats/min | identity |
| SBP | SysABP else NISysABP | mmHg | mmHg | mmHg | identity; invasive preferred per hour |
| MAP | MAP else NIMAP | mmHg | mmHg | mmHg | identity; invasive preferred per hour |
| DBP | DiasABP else NIDiasABP | mmHg | mmHg | mmHg | identity; invasive preferred per hour |
| O2Sat | SaO2 | % arterial SaO2 | % pulse oximetry | % | identity; FLAG different measurement modality |
| Resp | RespRate | breaths/min | breaths/min | breaths/min | identity |
| FiO2 | FiO2 | fraction (0-1) | % | fraction (0-1) | FLAG metadata conflict; preserve empirical 2019 fraction scale, no x100 |
| PaCO2 | PaCO2 | mmHg | mmHg | mmHg | identity |
| Creatinine | Creatinine | mg/dL | mg/dL | mg/dL | identity |
| BUN | BUN | mg/dL | mg/dL | mg/dL | identity |
| Potassium | K | mEq/L | mmol/L | mmol/L | x1; monovalent potassium |
| Lactate | Lactate | mmol/L | mg/dL | mmol/L-like frozen numeric scale | FLAG metadata conflict; preserve numerical scale, no x9.008 |
| Glucose | Glucose | mg/dL | mg/dL | mg/dL | identity; no glucose x18 or /18 |
| HCO3 | HCO3 | mmol/L | mmol/L | mmol/L | identity |
| WBC | WBC | cells/nL | 10^3 cells/uL | 10^3 cells/uL | x1; 1 nL = 0.001 uL |
| Temp | Temp | deg C | deg C | deg C | identity; no Fahrenheit transform |

All applied transforms have numeric multiplier 1 and offset 0. Potassium and WBC require a change of unit notation with no numeric change. Glucose is mg/dL in both sources; temperature is degrees Celsius in both. No percent conversion is applied to SaO2.

The local 2019 documentation calls FiO2 '%' and lactate 'mg/dL', but the frozen array is fraction-valued for FiO2 and mmol/L-like for lactate. Multiplying the 2012 values by 100 or 9.008 would force the transfer inputs away from the frozen training scale. This build preserves the observed numerical convention and flags the documentation conflict. A maintainer should verify primary-source provenance before claiming complete physical-unit harmonization; any revised lactate scale is a protocol change requiring a regenerated transfer artifact. SaO2 and O2Sat also differ in measurement modality (arterial versus pulse oximetry), even though both use percent; this mandated mapping is a limitation of the transfer comparison.

Frozen 2019 A observed-value checks (quantiles 1%, 50%, 99%; all A rows, not just A train):

| Variable | q01 | median | q99 | Frozen A-train mean | Frozen A-train std |
|---|---:|---:|---:|---:|---:|
| FiO2 | 0.3 | 0.5 | 1 | 0.529819 | 0.187731 |
| Lactate | 0.6 | 1.8 | 12.802 | 2.46163 | 2.19313 |
| Glucose | 61 | 124 | 321 | 133.903 | 51.7015 |
| Temp | 35.1 | 37 | 38.83 | 37.0141 | 0.776619 |
| WBC | 2.5 | 10.9 | 32.4 | 11.9907 | 6.8822 |
| Potassium | 2.9 | 4.1 | 6.1 | 4.16857 | 0.639647 |

## Static descriptors and unavailable labels

The within-2012 static vector is [Age (years), Gender (0 female, 1 male), Height (cm), Weight (kg), ICUType (1 coronary care, 2 cardiac surgery recovery, 3 medical ICU, 4 surgical ICU)]. These are raw admission descriptors, without standardization or one-hot expansion. Unknown values remain -1, with separate A_static_mask/B_static_mask metadata. Only the first 00:00 descriptor is used; later weight observations never fill missing admission weight. Set B record 149509 repeats weight at 00:00 (70.8 then 70.4); the first value, 70.8, is used.

| Descriptor | A missing | B missing |
|---|---:|---:|
| Age | 0 | 0 |
| Gender | 3 | 5 |
| Height | 1894 | 1930 |
| Weight | 326 | 347 |
| ICUType | 0 | 0 |

The transfer artifact instead supplies [Age, Gender, Unit1, Unit2, HospAdmTime], matching the semantic layout consumed by the 2019 models. Unit1 is 1 for ICUType=3, Unit2 is 1 for ICUType=4; other ICU types yield 0/0. Unavailable HospAdmTime and unknown Age/Gender use zero, matching the 2019 preprocessor's missing-value encoding. Original 2012 statics remain in A_static2012/B_static2012. ICU-type mapping is an explicit approximation: 2012 unit types are not the 2019 hospital administrative identifiers. The models consume statics, so the raw [Height, Weight, ICUType] slots must not be passed into a 2019 checkpoint.

2012 does not supply the 2019 SepsisLabel sequence. A_sepsis/B_sepsis and A_ever_sepsis/B_ever_sepsis are zero placeholders solely for loader compatibility, and sepsis_labels_available=False. They must not be interpreted as known nonseptic labels or used for sepsis-stratified conclusions. Outcomes-a.txt is hashed for provenance but is not used: mortality is not a sepsis label.

## Normalization and loader use

cinc2012_cohort.npz contains every original 2019 NPZ key with matching dtypes and trailing shapes, plus explicit protocol metadata, record IDs and both normalizations. A_* is set A and B_* is set B. Stored values are unnormalized. norm_mean/norm_std and norm_mean_within2012/norm_std_within2012 are fitted only on the 3,400 A-train stays, over observed hourly means, using exactly the 2019 estimator (population std + 1e-6; fallback mean=0/std=1 if <=10 cells). Eligible-window filtering happens later in the loader, as in 2019. norm_mean_transfer2019/norm_std_transfer2019 are exact copies of the frozen 2019 statistics, not re-estimates.

For the within-2012 run call make_loaders('cinc2012_cohort.npz', C=12, K=12, num_workers=0). Train on the first loader, select with the second, and evaluate on the fourth (testB). The third loader (testA) is intentionally empty because this card allocates all of A to train/validation. The generic training runner assumes a nonempty testA, so it must not be used blindly as a within-2012 evaluation wrapper.

For frozen-checkpoint transfer call make_loaders('cinc2012_transfer.npz', C=12, K=12, num_workers=0) and evaluate both the third and fourth loaders, comprising all eligible A and B stays. Combine masked error numerators and observed-target denominators across both sets; do not average set RMSEs. Transfer testA includes all 4,000 A indices. The unchanged make_loaders always creates a shuffled training loader and rejects an empty training dataset, so transfer train/val indices are retained only as compatibility handles and overlap testA. training_allowed=False records this restriction. Never fit or select a transfer model on those first two loaders; use the already frozen 2019 checkpoint. The primary artifact also stores transfer_A_test_idx/transfer_B_test_idx for direct evaluation without this view.

## Parsing audit

| Item | A | B |
|---|---:|---:|
| Mapped raw rows | 1254158 | 1257868 |
| Mapped rows outside [0,48) | 318 | 335 |
| Invalid negative/nonfinite Temp readings inside grid | 24 | 17 |
| Selected hourly cells from SysABP | 103377 | 103934 |
| Selected hourly cells from NISysABP | 66776 | 66502 |
| Selected hourly cells from MAP | 102800 | 103394 |
| Selected hourly cells from NIMAP | 66032 | 65651 |
| Selected hourly cells from DiasABP | 103365 | 103923 |
| Selected hourly cells from NIDiasABP | 66770 | 66484 |

All invalid mapped readings are negative temperatures (A: 23 at -17.8 and 1 at -12.5; B: 16 at -17.8 and 1 at -12.8). They are masked rather than interpreted as valid Celsius observations. Zeros and positive outliers, including extreme WBC readings, are retained under the no-additional-cleaning protocol. Detailed counters, input hashes and environment are in BUILD_SUMMARY.json; per-record split and length membership is in COHORT_MANIFEST.tsv.

## Verification

The public smoke tests exercise hourly pressure fallback, observation masks,
source timeline length, loader compatibility and numerical model checks.
Complete cohort archive and array hashes are in `manifests/cohorts.json`;
run `python3 tools/verify_cohorts.py` after rebuilding both views as described
in `REPRODUCE.md`. The full build census above is retained as frozen evidence.
