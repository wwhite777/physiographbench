# E3 current-archive rerun addendum — release 1.2.0

All **4/4 authorized reruns completed with exit code 0**, using the current manifest-validated archives, CPU and two threads. The effective main grid now contains 156 original records and four explicit replacements; **160/160 effective records match their current archive hashes**. No archive was regenerated or modified. The original [E3_READING.md](E3_READING.md), summary, run records and scientific freezes are preserved.

The main scientific interpretation is unchanged: broader measured support is associated with much better direction recovery at fixed measured rank dependence; increasing dependence over the tested modest range gives a smaller descriptive decline with wide seed uncertainty; repaired CRN-lite has no consistent exact-direction advantage over Control-GRU. Two narrower numerical statements change: the shared anchor no longer has bit-identical RMSE in every model/seed pair, and one nominal heart-rate RMSE interval now excludes zero, as detailed below. No causal-identification or independent scientific-review PASS is inferred.

This addendum reports an authored rerun and reconciliation; it does not constitute independent scientific review. The separate randomized-dose comparator gap was already resolved by the [matched-control addendum](E3_READING_ADDENDUM.md); its results are unchanged. Read this addendum with that diagnostic addendum, rather than treating the original report’s historical unavailable-comparator wording as current.

Full binary64 round-trip values, source hashes, per-seed counts, all recomputed main aggregates and paired differences, and original/replacement lineage are in [e3_summary_rerun.json](e3_summary_rerun.json). [E3_EFFECTIVE_INVENTORY.json](E3_EFFECTIVE_INVENTORY.json) identifies the distributed effective and superseded run records. The summary retains original commands, exit codes, hashes and UTC times; its source hashes refer to pre-distribution bytes. Use the inventory for hashes of the sanitized public records. Historical archive, log, checkpoint and prediction locators do not imply that those files are bundled. Logical run IDs stay stable; each row’s `source.file` identifies its effective physical record and `supersedes_source` identifies the retained original.

## Records and archive validation

SHA-256 is the archive’s byte-level cryptographic hash. All three current archives pass `sim_policy_ext3.validate_manifest`, including generator-code hashes. The four original command lines were preserved except for the required output directory and thread count. A bootstrap changes only the runner’s import-time scratch-directory constant in memory and disables dataset generation; no fit function or source file is changed. The default cache key is asserted to select the validated existing archive.

| Family / point / model / seed | Archive | Stored dataset SHA-256 | Current archive SHA-256 |
| --- | --- | --- | --- |
| support_only/point2/physiograph_gru/seed0 | 16c279d0f5dd9065e2db.npz | `04641ccc94aab403639a24ab6ec043bda767d9d6a0955876bec449fd5c69bbf9` | `b89e7f71b5e31177983c17bcb2353cd8a3fd767faa22f7ca32e561455905f0e4` |
| support_only/point1/crn_lite/seed3 | 18c6c14bdd7f8b47dd73.npz | `7cf76268ca9faaad032c8caaf57bc8992efde4403f469ef110039459951e5915` | `3c087f996880b3227a3facdc56141c8173d81953cddcb08db852570f75d8012f` |
| support_only/point1/physiograph/seed1 | 18c6c14bdd7f8b47dd73.npz | `7cf76268ca9faaad032c8caaf57bc8992efde4403f469ef110039459951e5915` | `3c087f996880b3227a3facdc56141c8173d81953cddcb08db852570f75d8012f` |
| dependence_only/point4/crn_lite/seed3 | e70bf6f71307c2baf727.npz | `5ada696d43ce59d54c30bdca7cb999cc254bdd1b675ee497021ad0c2fa716324` | `09e76adecca567e8ab7b15e87f46ea45d552248cd2ddc5815c847dfc0cb5e050` |

Saved train/test patient indices, training normalization, policy metadata, support intervals, onset/history checks and all assignment-target distributions match each original record. Every rerun’s saved test truth matches both its current archive and the original saved test truth exactly. This certifies the replacement inputs and outputs; it does not reconstruct the unavailable historical training arrays.

## Per-run metric changes

A direction cell is test patient × adjacent dose pair × scored time × physiological channel. Exact post-effect accuracy compares signs where the true adjacent-dose change is nonzero. The tolerance score first maps magnitudes at or below a channel-specific threshold to zero in both truth and prediction, then scores nonzero thresholded truth. Thresholds for mean arterial pressure (MAP), heart rate (HR), cardiac output (CO), central venous pressure (CVP), urine output (UO) and lactate (Lac) are respectively [0.1 mmHg, 0.1 beats/min, 0.01 L/min, 0.05 mmHg, 0.01 mL/min, 0.01 mmol/L]. They are numerical sensitivity thresholds. All fits use 60 epochs; exact N is 60,480 per run. Exact zero-effect accuracy remains null (0/0).

| Record | Exact before | Exact after | Exact Δ | Tolerance post-effect before | Tolerance post-effect after | Tolerance Δ |
| --- | --- | --- | --- | --- | --- | --- |
| support_only/point2/physiograph_gru/seed0 | 0.779993 (47174/60480) | 0.779960 (47172/60480) | -0.000033069 | 0.178257 (10184/57131) | 0.178292 (10186/57131) | 0.000035007 |
| support_only/point1/crn_lite/seed3 | 0.361359 (21855/60480) | 0.361343 (21854/60480) | -0.000016534 | 0.154979 (8745/56427) | 0.154979 (8745/56427) | 0.000000000 |
| support_only/point1/physiograph/seed1 | 0.329084 (19903/60480) | 0.330671 (19999/60480) | 0.001587302 | 0.155997 (8860/56796) | 0.163568 (9290/56796) | 0.007570956 |
| dependence_only/point4/crn_lite/seed3 | 0.918700 (55563/60480) | 0.918700 (55563/60480) | 0.000000000 | 0.787105 (44414/56427) | 0.787105 (44414/56427) | 0.000000000 |

Physical-unit root mean squared error (RMSE) uses 12,600 scored patient × alternative-dose × time values per channel per run. Each cell below is before → after (after − before); unlike units are never averaged. Nine decimal places expose small changes; full precision is in the JSON.

| Record | MAP (mmHg) | HR (beats/min) | CO (L/min) | CVP (mmHg) | UO (mL/min) | Lac (mmol/L) |
| --- | --- | --- | --- | --- | --- | --- |
| support_only/point2/physiograph_gru/seed0 | 7.285584195 → 7.285298460 (-0.000285734) | 3.932040010 → 3.932089286 (0.000049276) | 0.116708812 → 0.116709612 (0.000000799) | 0.598259648 → 0.598272719 (0.000013071) | 0.141973196 → 0.141959723 (-0.000013473) | 0.757577369 → 0.757556373 (-0.000020996) |
| support_only/point1/crn_lite/seed3 | 8.172737580 → 8.172737477 (-0.000000103) | 4.373602391 → 4.373602450 (0.000000059) | 0.146736133 → 0.146736118 (-0.000000015) | 0.632999811 → 0.632999792 (-0.000000019) | 0.167543148 → 0.167543147 (-0.000000001) | 0.825034233 → 0.825034217 (-0.000000016) |
| support_only/point1/physiograph/seed1 | 9.432949158 → 8.636581216 (-0.796367942) | 6.676926658 → 6.092727926 (-0.584198731) | 0.319977952 → 0.408779205 (0.088801252) | 0.976269779 → 1.225740497 (0.249470718) | 0.158970115 → 0.156104162 (-0.002865952) | 0.977915732 → 0.826812768 (-0.151102963) |
| dependence_only/point4/crn_lite/seed3 | 7.023730362 → 7.023730638 (0.000000276) | 3.780957613 → 3.780957775 (0.000000163) | 0.122902832 → 0.122902831 (-0.000000002) | 0.651928795 → 0.651928823 (0.000000028) | 0.146248343 → 0.146248348 (0.000000005) | 0.777212778 → 0.777212795 (0.000000016) |

The original fits used one CPU thread; these required reruns use two. Observed changes therefore combine archive replacement and thread-count variation. This task does not isolate their separate contributions. In particular, the larger SSM RMSE shift is reported rather than attributed solely to the archive race. Saved predictions were independently rescored: all exact/tolerance counts agree exactly and RMSE agrees within 2.69 × 10⁻¹⁶ relative difference after archive serialization.

## CRN-lite target distributions

CRN-lite is the lightweight counterfactual recurrent network whose adversarial auxiliary head predicts assigned eventual factual dose during training. Its all/train/test target distributions are exactly unchanged in both reruns, including unique counts, minima/maxima, means, standard deviations, all seven quantiles and all ten histogram bins. All 40 effective CRN-lite fits and 120 split distributions remain nonconstant. Minimum unique counts are 265/208/102 and minimum standard deviations are 0.014542/0.014050/0.014113 for all/train/test. Nonconstant targets make the balancing probe operational; they do not demonstrate successful balancing or distributional independence.

## Every affected original reading table, before and after

The nine tables below include every printed table that consumes a replacement: 30 affected rows, each shown before and after. Rows unchanged at six decimal places are included explicitly, including dependence point 4 and its exact-direction endpoint interval. All 40 main aggregate groups, 30 model-comparison groups and eight family trends were recomputed from the effective records. Unaffected diagnostic and historical summaries remain as supplied; no other model was trained.

Means use four model/split seeds and sample standard deviations. A paired difference is metric A minus metric B within the same seed and patient split; its 95% confidence interval (CI) is mean(d) ± 3.182446305284263 × sample_sd(d)/√4. Sign counts are positive/zero/negative unrounded differences. These are nominal seed/split intervals conditional on one cohort, without patient-sampling inference or multiplicity correction. Tolerance A/P/Z means all/post-effect/zero-effect; restricted scores require both adjacent doses inside the patient’s severity-tercile central support interval. Empty subsets remain null.

### One-dimensional reading: support at fixed dependence — original table 2

| Version | Point | Control-GRU post-effect | CRN-lite post-effect | PhysioGraph-GRU post-effect | PhysioGraph (SSM) post-effect |
| --- | --- | --- | --- | --- | --- |
| Before | 1 | 0.386314 ± 0.095164 (N=60480/seed) | 0.389654 ± 0.093479 (N=60480/seed) | 0.341481 ± 0.095457 (N=60480/seed) | 0.407614 ± 0.151705 (N=60480/seed) |
| After | 1 | 0.386314 ± 0.095164 (N=60480/seed) | 0.389649 ± 0.093481 (N=60480/seed) | 0.341481 ± 0.095457 (N=60480/seed) | 0.408011 ± 0.151433 (N=60480/seed) |
| Before | 2 | 0.656374 ± 0.198109 (N=60480/seed) | 0.709867 ± 0.230516 (N=60480/seed) | 0.742125 ± 0.088819 (N=60480/seed) | 0.587591 ± 0.038409 (N=60480/seed) |
| After | 2 | 0.656374 ± 0.198109 (N=60480/seed) | 0.709867 ± 0.230516 (N=60480/seed) | 0.742117 ± 0.088814 (N=60480/seed) | 0.587591 ± 0.038409 (N=60480/seed) |

### One-dimensional reading: dependence at fixed support — original table 4

| Version | Point | Control-GRU post-effect | CRN-lite post-effect | PhysioGraph-GRU post-effect | PhysioGraph (SSM) post-effect |
| --- | --- | --- | --- | --- | --- |
| Before | 4 | 0.908548 ± 0.062189 (N=60480/seed) | 0.909317 ± 0.069149 (N=60480/seed) | 0.896681 ± 0.040697 (N=60480/seed) | 0.890480 ± 0.048738 (N=60480/seed) |
| After | 4 | 0.908548 ± 0.062189 (N=60480/seed) | 0.909317 ± 0.069149 (N=60480/seed) | 0.896681 ± 0.040697 (N=60480/seed) | 0.890480 ± 0.048738 (N=60480/seed) |

### One-dimensional reading: dependence at fixed support — original table 5

| Version | Model | Mean difference [95% paired t CI] | Sign +/0/− |
| --- | --- | --- | --- |
| Before | CRN-lite | -0.081667 [-0.187281, 0.023946] (A:N=60480/seed; B:N=60480/seed) | 1/0/3 |
| After | CRN-lite | -0.081667 [-0.187281, 0.023946] (A:N=60480/seed; B:N=60480/seed) | 1/0/3 |

### Repaired CRN-lite and model contrasts — original table 6

| Version | Family | Point | A − Control-GRU | Exact post-effect Δ [95% CI] | Sign +/0/− | Tolerance post-effect Δ [95% CI] | Sign +/0/− |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Before | support_only | 1 | CRN-lite | 0.003340 [-0.006137, 0.012817] (A:N=60480/seed; B:N=60480/seed) | 2/0/2 | -0.004763 [-0.044312, 0.034787] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 3/0/1 |
| After | support_only | 1 | CRN-lite | 0.003336 [-0.006128, 0.012800] (A:N=60480/seed; B:N=60480/seed) | 2/0/2 | -0.004763 [-0.044312, 0.034787] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 3/0/1 |
| Before | support_only | 1 | PhysioGraph (SSM) | 0.021300 [-0.191311, 0.233912] (A:N=60480/seed; B:N=60480/seed) | 1/0/3 | 0.072205 [-0.136493, 0.280902] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 3/0/1 |
| After | support_only | 1 | PhysioGraph (SSM) | 0.021697 [-0.190742, 0.234137] (A:N=60480/seed; B:N=60480/seed) | 1/0/3 | 0.074097 [-0.133797, 0.281991] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 3/0/1 |
| Before | support_only | 2 | PhysioGraph-GRU | 0.085751 [-0.103481, 0.274984] (A:N=60480/seed; B:N=60480/seed) | 4/0/0 | -0.086241 [-0.168776, -0.003706] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 0/0/4 |
| After | support_only | 2 | PhysioGraph-GRU | 0.085743 [-0.103500, 0.274987] (A:N=60480/seed; B:N=60480/seed) | 4/0/0 | -0.086232 [-0.168750, -0.003715] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 0/0/4 |
| Before | dependence_only | 4 | CRN-lite | 0.000769 [-0.032322, 0.033859] (A:N=60480/seed; B:N=60480/seed) | 2/0/2 | 0.006573 [-0.008848, 0.021994] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 3/0/1 |
| After | dependence_only | 4 | CRN-lite | 0.000769 [-0.032322, 0.033859] (A:N=60480/seed; B:N=60480/seed) | 2/0/2 | 0.006573 [-0.008848, 0.021994] (A:N(seed0–3)=[57131,56796,57043,56427]; B:N(seed0–3)=[57131,56796,57043,56427]) | 3/0/1 |

### Four-seed tolerance and restricted summaries — original table 11

| Version | Family | Point | Model | Tolerance all | Tolerance post-effect | Tolerance zero-effect | Restricted exact post-effect |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Before | support_only | 1 | CRN-lite | 0.181820 ± 0.027457 (N=60480/seed) | 0.139856 ± 0.033818 (N(seed0–3)=[57131,56796,57043,56427]) | 0.840608 ± 0.099820 (N(seed0–3)=[3349,3684,3437,4053]) | null ± null (N=0/seed) |
| After | support_only | 1 | CRN-lite | 0.181820 ± 0.027457 (N=60480/seed) | 0.139856 ± 0.033818 (N(seed0–3)=[57131,56796,57043,56427]) | 0.840608 ± 0.099820 (N(seed0–3)=[3349,3684,3437,4053]) | null ± null (N=0/seed) |
| Before | support_only | 1 | PhysioGraph (SSM) | 0.251525 ± 0.117469 (N=60480/seed) | 0.216823 ± 0.125255 (N(seed0–3)=[57131,56796,57043,56427]) | 0.785803 ± 0.107256 (N(seed0–3)=[3349,3684,3437,4053]) | null ± null (N=0/seed) |
| After | support_only | 1 | PhysioGraph (SSM) | 0.254468 ± 0.115702 (N=60480/seed) | 0.218716 ± 0.124081 (N(seed0–3)=[57131,56796,57043,56427]) | 0.804940 ± 0.114795 (N(seed0–3)=[3349,3684,3437,4053]) | null ± null (N=0/seed) |
| Before | support_only | 2 | PhysioGraph-GRU | 0.242684 ± 0.090362 (N=60480/seed) | 0.198582 ± 0.089621 (N(seed0–3)=[57131,56796,57043,56427]) | 0.937033 ± 0.070798 (N(seed0–3)=[3349,3684,3437,4053]) | null ± null (N=0/seed) |
| After | support_only | 2 | PhysioGraph-GRU | 0.242692 ± 0.090360 (N=60480/seed) | 0.198590 ± 0.089619 (N(seed0–3)=[57131,56796,57043,56427]) | 0.937033 ± 0.070798 (N(seed0–3)=[3349,3684,3437,4053]) | null ± null (N=0/seed) |
| Before | dependence_only | 4 | CRN-lite | 0.772640 ± 0.053379 (N=60480/seed) | 0.781781 ± 0.054135 (N(seed0–3)=[57131,56796,57043,56427]) | 0.628150 ± 0.080188 (N(seed0–3)=[3349,3684,3437,4053]) | 0.908868 ± 0.069225 (N=45360/seed) |
| After | dependence_only | 4 | CRN-lite | 0.772640 ± 0.053379 (N=60480/seed) | 0.781781 ± 0.054135 (N(seed0–3)=[57131,56796,57043,56427]) | 0.628150 ± 0.080188 (N(seed0–3)=[3349,3684,3437,4053]) | 0.908868 ± 0.069225 (N=45360/seed) |

### Physical-unit RMSE: four-seed means ± sd — original table 12

| Version | Family | Point | Model | MAP (mmHg) | HR (beats/min) | CO (L/min) | CVP (mmHg) | UO (mL/min) | Lac (mmol/L) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Before | support_only | 1 | CRN-lite | 8.062896 ± 0.429132 | 4.442231 ± 0.382132 | 0.136597 ± 0.018545 | 0.584207 ± 0.043020 | 0.165345 ± 0.021580 | 0.829628 ± 0.070190 |
| After | support_only | 1 | CRN-lite | 8.062896 ± 0.429132 | 4.442231 ± 0.382132 | 0.136597 ± 0.018545 | 0.584207 ± 0.043020 | 0.165345 ± 0.021580 | 0.829628 ± 0.070190 |
| Before | support_only | 1 | PhysioGraph (SSM) | 9.098092 ± 0.559090 | 5.431181 ± 0.878787 | 0.292407 ± 0.094143 | 1.249957 ± 0.535716 | 0.173678 ± 0.014427 | 0.857904 ± 0.117784 |
| After | support_only | 1 | PhysioGraph (SSM) | 8.899000 ± 0.541620 | 5.285131 ± 0.610257 | 0.314607 ± 0.111654 | 1.312324 ± 0.506984 | 0.172961 ± 0.015437 | 0.820128 ± 0.086554 |
| Before | support_only | 2 | PhysioGraph-GRU | 7.718999 ± 0.411282 | 4.404482 ± 0.436396 | 0.139464 ± 0.017188 | 0.638999 ± 0.034141 | 0.150300 ± 0.016319 | 0.822251 ± 0.084267 |
| After | support_only | 2 | PhysioGraph-GRU | 7.718928 ± 0.411382 | 4.404495 ± 0.436378 | 0.139464 ± 0.017188 | 0.639002 ± 0.034136 | 0.150297 ± 0.016321 | 0.822246 ± 0.084272 |
| Before | dependence_only | 4 | CRN-lite | 6.886728 ± 0.179574 | 3.818133 ± 0.211853 | 0.112729 ± 0.015254 | 0.586296 ± 0.053936 | 0.144236 ± 0.014327 | 0.777539 ± 0.045323 |
| After | dependence_only | 4 | CRN-lite | 6.886728 ± 0.179574 | 3.818133 ± 0.211853 | 0.112729 ± 0.015254 | 0.586296 ± 0.053936 | 0.144236 ± 0.014327 | 0.777539 ± 0.045323 |

### Physical-unit RMSE: four-seed means ± sd — original table 13

| Version | Family | Point | A − Control-GRU | MAP (mmHg) | HR (beats/min) | CO (L/min) | CVP (mmHg) | UO (mL/min) | Lac (mmol/L) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Before | support_only | 1 | CRN-lite | -0.013120 [-0.080731, 0.054490] {2/0/2} | 0.018184 [-0.030103, 0.066470] {3/0/1} | -0.001112 [-0.010426, 0.008202] {1/0/3} | -0.001195 [-0.007307, 0.004918] {2/0/2} | 0.000793 [-0.000258, 0.001844] {3/0/1} | -0.001124 [-0.006021, 0.003773] {2/0/2} |
| After | support_only | 1 | CRN-lite | -0.013120 [-0.080731, 0.054490] {2/0/2} | 0.018184 [-0.030103, 0.066470] {3/0/1} | -0.001112 [-0.010426, 0.008202] {1/0/3} | -0.001195 [-0.007307, 0.004918] {2/0/2} | 0.000793 [-0.000258, 0.001844] {3/0/1} | -0.001124 [-0.006021, 0.003773] {2/0/2} |
| Before | support_only | 1 | PhysioGraph (SSM) | 1.022076 [-0.449772, 2.493924] {4/0/0} | 1.007134 [-0.233556, 2.247824] {4/0/0} | 0.154698 [0.010975, 0.298421] {4/0/0} | 0.664555 [-0.242805, 1.571915] {4/0/0} | 0.009125 [-0.003447, 0.021697] {3/0/1} | 0.027152 [-0.154200, 0.208503] {2/0/2} |
| After | support_only | 1 | PhysioGraph (SSM) | 0.822984 [-0.641000, 2.286968] {4/0/0} | 0.861084 [0.079426, 1.642743] {4/0/0} | 0.176898 [0.016214, 0.337582] {4/0/0} | 0.726923 [-0.133370, 1.587215] {4/0/0} | 0.008409 [-0.004231, 0.021049] {3/0/1} | -0.010624 [-0.090300, 0.069052] {2/0/2} |
| Before | support_only | 2 | PhysioGraph-GRU | -0.010255 [-0.390475, 0.369964] {2/0/2} | 0.224443 [0.022723, 0.426163] {4/0/0} | 0.014693 [-0.009575, 0.038961] {3/0/1} | 0.051078 [0.002751, 0.099405] {4/0/0} | -0.008396 [-0.012726, -0.004066] {0/0/4} | 0.014476 [-0.027344, 0.056296] {3/0/1} |
| After | support_only | 2 | PhysioGraph-GRU | -0.010327 [-0.390596, 0.369943] {2/0/2} | 0.224455 [0.022754, 0.426157] {4/0/0} | 0.014693 [-0.009574, 0.038961] {3/0/1} | 0.051081 [0.002750, 0.099412] {4/0/0} | -0.008399 [-0.012720, -0.004078] {0/0/4} | 0.014471 [-0.027360, 0.056302] {3/0/1} |
| Before | dependence_only | 4 | CRN-lite | -0.025556 [-0.196689, 0.145577] {2/0/2} | -0.033035 [-0.111539, 0.045470] {2/0/2} | -0.000792 [-0.011510, 0.009926] {2/0/2} | -0.001550 [-0.023962, 0.020862] {3/0/1} | 0.001066 [-0.002495, 0.004628] {2/0/2} | -0.000123 [-0.007328, 0.007081] {2/0/2} |
| After | dependence_only | 4 | CRN-lite | -0.025556 [-0.196689, 0.145578] {2/0/2} | -0.033035 [-0.111539, 0.045470] {2/0/2} | -0.000792 [-0.011510, 0.009926] {2/0/2} | -0.001550 [-0.023962, 0.020862] {3/0/1} | 0.001066 [-0.002495, 0.004628] {2/0/2} | -0.000123 [-0.007328, 0.007081] {2/0/2} |

### All main runs: 160 rows — original table 15

| Version | Family | Point | Model | Seed | Status | Epochs | Exact post-effect | Exact zero-effect | Tolerance A | Tolerance P | Tolerance Z | RMSE vector | Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Before | support_only | 1 | CRN-lite | 3 | complete | 60 | 0.361359 (21855/60480) | null (0/0) | 0.199256 (12051/60480) | 0.154979 (8745/56427) | 0.815692 (3306/4053) | 8.172738; 4.373602; 0.146736; 0.633000; 0.167543; 0.825034 | [run](main/support_only/point1/crn_lite/seed3/run.json) |
| After | support_only | 1 | CRN-lite | 3 | complete | 60 | 0.361343 (21854/60480) | null (0/0) | 0.199256 (12051/60480) | 0.154979 (8745/56427) | 0.815692 (3306/4053) | 8.172737; 4.373602; 0.146736; 0.633000; 0.167543; 0.825034 | [run](main_rerun/support_only/point1/crn_lite/seed3/run.json) |
| Before | support_only | 1 | PhysioGraph (SSM) | 1 | complete | 60 | 0.329084 (19903/60480) | null (0/0) | 0.194610 (11770/60480) | 0.155997 (8860/56796) | 0.789902 (2910/3684) | 9.432949; 6.676927; 0.319978; 0.976270; 0.158970; 0.977916 | [run](main/support_only/point1/physiograph/seed1/run.json) |
| After | support_only | 1 | PhysioGraph (SSM) | 1 | complete | 60 | 0.330671 (19999/60480) | null (0/0) | 0.206382 (12482/60480) | 0.163568 (9290/56796) | 0.866450 (3192/3684) | 8.636581; 6.092728; 0.408779; 1.225740; 0.156104; 0.826813 | [run](main_rerun/support_only/point1/physiograph/seed1/run.json) |
| Before | support_only | 2 | PhysioGraph-GRU | 0 | complete | 60 | 0.779993 (47174/60480) | null (0/0) | 0.223528 (13519/60480) | 0.178257 (10184/57131) | 0.995820 (3335/3349) | 7.285584; 3.932040; 0.116709; 0.598260; 0.141973; 0.757577 | [run](main/support_only/point2/physiograph_gru/seed0/run.json) |
| After | support_only | 2 | PhysioGraph-GRU | 0 | complete | 60 | 0.779960 (47172/60480) | null (0/0) | 0.223562 (13521/60480) | 0.178292 (10186/57131) | 0.995820 (3335/3349) | 7.285298; 3.932089; 0.116710; 0.598273; 0.141960; 0.757556 | [run](main_rerun/support_only/point2/physiograph_gru/seed0/run.json) |
| Before | dependence_only | 4 | CRN-lite | 3 | complete | 60 | 0.918700 (55563/60480) | null (0/0) | 0.775777 (46919/60480) | 0.787105 (44414/56427) | 0.618061 (2505/4053) | 7.023730; 3.780958; 0.122903; 0.651929; 0.146248; 0.777213 | [run](main/dependence_only/point4/crn_lite/seed3/run.json) |
| After | dependence_only | 4 | CRN-lite | 3 | complete | 60 | 0.918700 (55563/60480) | null (0/0) | 0.775777 (46919/60480) | 0.787105 (44414/56427) | 0.618061 (2505/4053) | 7.023731; 3.780958; 0.122903; 0.651929; 0.146248; 0.777213 | [run](main_rerun/dependence_only/point4/crn_lite/seed3/run.json) |

### CRN-lite auxiliary target: every policy/seed/split — original table 16

| Version | Family | Point | Seed | Split | N | Unique | Min | Max | Mean | Std | Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Before | support_only | 1 | 3 | all | 400 | 265 | 0.187500 | 0.312500 | 0.250000 | 0.036356 | [run](main/support_only/point1/crn_lite/seed3/run.json) |
| After | support_only | 1 | 3 | all | 400 | 265 | 0.187500 | 0.312500 | 0.250000 | 0.036356 | [run](main_rerun/support_only/point1/crn_lite/seed3/run.json) |
| Before | support_only | 1 | 3 | train | 280 | 209 | 0.187500 | 0.312500 | 0.250396 | 0.035126 | [run](main/support_only/point1/crn_lite/seed3/run.json) |
| After | support_only | 1 | 3 | train | 280 | 209 | 0.187500 | 0.312500 | 0.250396 | 0.035126 | [run](main_rerun/support_only/point1/crn_lite/seed3/run.json) |
| Before | support_only | 1 | 3 | test | 120 | 107 | 0.187500 | 0.312500 | 0.249076 | 0.039061 | [run](main/support_only/point1/crn_lite/seed3/run.json) |
| After | support_only | 1 | 3 | test | 120 | 107 | 0.187500 | 0.312500 | 0.249076 | 0.039061 | [run](main_rerun/support_only/point1/crn_lite/seed3/run.json) |
| Before | dependence_only | 4 | 3 | all | 400 | 265 | 0.000000 | 0.500000 | 0.250000 | 0.145424 | [run](main/dependence_only/point4/crn_lite/seed3/run.json) |
| After | dependence_only | 4 | 3 | all | 400 | 265 | 0.000000 | 0.500000 | 0.250000 | 0.145424 | [run](main_rerun/dependence_only/point4/crn_lite/seed3/run.json) |
| Before | dependence_only | 4 | 3 | train | 280 | 209 | 0.000000 | 0.500000 | 0.251584 | 0.140502 | [run](main/dependence_only/point4/crn_lite/seed3/run.json) |
| After | dependence_only | 4 | 3 | train | 280 | 209 | 0.000000 | 0.500000 | 0.251584 | 0.140502 | [run](main_rerun/dependence_only/point4/crn_lite/seed3/run.json) |
| Before | dependence_only | 4 | 3 | test | 120 | 107 | 0.000000 | 0.500000 | 0.246303 | 0.156245 | [run](main/dependence_only/point4/crn_lite/seed3/run.json) |
| After | dependence_only | 4 | 3 | test | 120 | 107 | 0.000000 | 0.500000 | 0.246303 | 0.156245 | [run](main_rerun/dependence_only/point4/crn_lite/seed3/run.json) |

The policy-coordinate table, support-family endpoint table, continuous-dose diagnostic tables and historical comparison table do not consume any replacement. Their numbers are unchanged. All six auxiliary-target rows above change only their source links. The dependence point-4 CRN-lite aggregate, its model contrast and endpoint direction interval remain identical in displayed accuracy, CI and sign count; their physical RMSE values are recomputed at full precision.

## Additional paired and conclusion checks

The affected dependence-family CRN-lite endpoint also contains channel-RMSE paired estimates in the JSON, although the original printed endpoint table shows only exact direction. These full-precision estimates were recomputed; they are identical at the displayed precision below. The four affected model-versus-Control-GRU RMSE rows, with every CI and sign count, appear in original table 13 above.

| Channel / units | Point 4 − point 0 before: mean [95% CI] {+/0/−} | After |
| --- | --- | --- |
| MAP / mmHg | 0.077777 [-0.472320, 0.627874] {3/0/1} | 0.077777 [-0.472320, 0.627874] {3/0/1} |
| HR / beats/min | 0.007372 [-0.205486, 0.220230] {3/0/1} | 0.007372 [-0.205486, 0.220230] {3/0/1} |
| CO / L/min | 0.001155 [-0.004602, 0.006912] {3/0/1} | 0.001155 [-0.004602, 0.006912] {3/0/1} |
| CVP / mmHg | 0.012291 [-0.022967, 0.047549] {3/0/1} | 0.012291 [-0.022967, 0.047549] {3/0/1} |
| UO / mL/min | 0.005615 [-0.003343, 0.014573] {3/0/1} | 0.005615 [-0.003343, 0.014573] {3/0/1} |
| Lac / mmol/L | 0.008699 [-0.019115, 0.036514] {3/0/1} | 0.008699 [-0.019115, 0.036514] {3/0/1} |

No exact/tolerance paired sign count or nominal direction-CI inclusion changes, across all main model contrasts and family endpoints. All support-family point-4-minus-point-0 exact direction differences remain positive in all four seeds; all dependence-family exact endpoint intervals still include zero. CRN-lite’s exact post-effect model-comparison intervals all include zero, and its largest positive mean contrast still occurs at support point 2.

One nominal RMSE inference changes: support-only point 1, PhysioGraph SSM minus Control-GRU, HR error changes from **1.007134 [-0.233556, 2.247824] {4/0/0} beats/min** to **0.861084 [0.079426, 1.642743] {4/0/0} beats/min**. The new CI lies above zero, indicating higher SSM HR error at that point under this seed-level summary; all four differences were already positive. No paired sign count changes anywhere. This does not change the original report’s stated support/dependence or direction-recovery conclusions, and it is not adjusted for the many reported intervals.

The original blanket statement that all 16 shared-anchor model/seed pairs have exactly equal RMSE is superseded: **15/16** retain exact equality. CRN-lite seed 3 has a largest absolute channel-RMSE difference of **2.7599983098980374 × 10⁻⁷ mmHg (MAP)** after rerunning only its dependence-family member. All 16 anchor pairs retain exactly equal direction scores and target distributions. The shared anchor remains one assignment design, not independent replication.

The archive-provenance limitation is resolved prospectively for this effective main grid. Historical records retain their original hashes, and the new summary explicitly supersedes only the four affected sources. Scientific interpretation remains limited to these policies, this cohort, the tested dependence range and these models. This engineering reconciliation does not constitute independent scientific review.

Generated 2026-11-06T02:05:56.664334+00:00 UTC.
