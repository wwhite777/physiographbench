# Shared-input renal control reading

RMSE@12 means root mean squared error pooled over observed targets across the next forecast horizon; it is not the error only at the final hour. A denotes A-test and B denotes the external hospital. Units are A-train standard deviations. Organ scores pool stays, hours, and that organ's variables; the all-organ score pools all observed targets. Seed means average per-run RMSEs, and spans are maximum minus minimum across seeds.

Giving every no-edge organ node all 16 dynamic variables and their masks lowers renal pooled RMSE in 4/4 paired seeds on both splits: the seed mean changes from 0.846332 to 0.712003 on A (shared − partitioned -0.134330) and from 1.067043 to 0.939610 on B (-0.127433). This is a one-factor input-scope control at a fixed selected configuration, not a retuned model. Both context and forecast-step inputs are widened, while both arms retain no edges, organ-specific output heads, static inputs, and the same forecast boundary/mask rules; shared forecast feedback carries the preceding predictions of all organs. The comparison also widens projection capacity (759952 versus 778384 parameters), so it does not distinguish input access from that capacity change. The unresolved alternatives named in RENAL_DIAGNOSIS.md remain optimization, forecast boundary handling, and missingness representation, including the lack of explicit elapsed-time inputs; recurrent-state/coupling handling is unchanged. This comparison does not resolve the frozen admissible-edge architecture or the separate CinC-2012 seed behavior. It reports direction and magnitude for these saved fits.

All 8 runs have status `complete`, with 35 completed epochs each; none is excluded. The exclusion rule is status `failed` or fewer than 10 completed epochs. The selected configuration is learning rate 0.000500, `large`, model width 96, state width 48, and 2 layers, with context and forecast lengths both 12 hours. Checkpoint selection uses validation scores. The run table shows recorded test RMSEs; each cell contains A / B in that order.

| Arm | Seed | Status | Epochs | Parameters | Cardiovascular A / B | Pulmonary A / B | Renal A / B | Metabolic A / B | All-organ pooled A / B |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| partitioned | 0 | complete | 35 | 759952 | 0.699532 / 0.800050 | 0.842732 / 0.818036 | 0.796462 / 1.018164 | 0.858934 / 0.856209 | 0.770099 / 0.817404 |
| partitioned | 1 | complete | 35 | 759952 | 0.698773 / 0.799773 | 0.842261 / 0.818595 | 0.932439 / 1.148013 | 0.873588 / 0.864174 | 0.776766 / 0.822623 |
| partitioned | 2 | complete | 35 | 759952 | 0.698510 / 0.796894 | 0.845032 / 0.818856 | 0.851380 / 1.081114 | 0.862824 / 0.859189 | 0.773010 / 0.818208 |
| partitioned | 3 | complete | 35 | 759952 | 0.699444 / 0.798893 | 0.840561 / 0.817066 | 0.805048 / 1.020880 | 0.858651 / 0.859271 | 0.769565 / 0.816888 |
| shared | 0 | complete | 35 | 778384 | 0.696719 / 0.800309 | 0.831976 / 0.813975 | 0.714097 / 0.941480 | 0.815623 / 0.830429 | 0.756991 / 0.811263 |
| shared | 1 | complete | 35 | 778384 | 0.694947 / 0.795241 | 0.833757 / 0.814245 | 0.712924 / 0.941381 | 0.817905 / 0.827041 | 0.756987 / 0.808053 |
| shared | 2 | complete | 35 | 778384 | 0.695585 / 0.797213 | 0.839006 / 0.815106 | 0.715663 / 0.944142 | 0.817470 / 0.833836 | 0.759251 / 0.810247 |
| shared | 3 | complete | 35 | 778384 | 0.696028 / 0.798686 | 0.835830 / 0.815224 | 0.705326 / 0.931436 | 0.823616 / 0.836131 | 0.758646 / 0.811004 |

Paired differences below are shared − partitioned. Negative values mean lower RMSE with shared input. Sign counts list negative / zero / positive out of the planned paired seeds.

| Split | Target | Seed 0 | Seed 1 | Seed 2 | Seed 3 | Mean | Minimum | Maximum | Signs − / zero / + |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | cardiovascular | -0.002812 | -0.003825 | -0.002925 | -0.003416 | -0.003245 | -0.003825 | -0.002812 | 4 / 0 / 0 out of 4 |
| A | pulmonary | -0.010755 | -0.008504 | -0.006027 | -0.004731 | -0.007504 | -0.010755 | -0.004731 | 4 / 0 / 0 out of 4 |
| A | renal | -0.082365 | -0.219515 | -0.135717 | -0.099722 | -0.134330 | -0.219515 | -0.082365 | 4 / 0 / 0 out of 4 |
| A | metabolic | -0.043311 | -0.055682 | -0.045354 | -0.035035 | -0.044846 | -0.055682 | -0.035035 | 4 / 0 / 0 out of 4 |
| A | all organ pooled | -0.013107 | -0.019779 | -0.013759 | -0.010918 | -0.014391 | -0.019779 | -0.010918 | 4 / 0 / 0 out of 4 |
| B | cardiovascular | +0.000259 | -0.004533 | +0.000319 | -0.000207 | -0.001040 | -0.004533 | +0.000319 | 2 / 0 / 2 out of 4 |
| B | pulmonary | -0.004060 | -0.004350 | -0.003751 | -0.001843 | -0.003501 | -0.004350 | -0.001843 | 4 / 0 / 0 out of 4 |
| B | renal | -0.076684 | -0.206632 | -0.136973 | -0.089444 | -0.127433 | -0.206632 | -0.076684 | 4 / 0 / 0 out of 4 |
| B | metabolic | -0.025779 | -0.037133 | -0.025353 | -0.023139 | -0.027851 | -0.037133 | -0.023139 | 4 / 0 / 0 out of 4 |
| B | all organ pooled | -0.006141 | -0.014570 | -0.007962 | -0.005884 | -0.008639 | -0.014570 | -0.005884 | 4 / 0 / 0 out of 4 |

Every other organ and the all-organ pooled score have lower four-seed mean RMSE with shared input on both splits. B cardiovascular RMSE rises in the seed pairs with positive differences shown above, so improvement is not uniform across all organ–seed combinations.

Arm means and seed spans follow. The interval is minimum–maximum, followed by its width; it describes variation across the saved seeds, not sampling uncertainty.

| Split | Target | Partitioned mean | Partitioned min–max | Partitioned span | Shared mean | Shared min–max | Shared span |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | cardiovascular | 0.699065 | 0.698510–0.699532 | 0.001022 | 0.695820 | 0.694947–0.696719 | 0.001772 |
| A | pulmonary | 0.842647 | 0.840561–0.845032 | 0.004471 | 0.835142 | 0.831976–0.839006 | 0.007029 |
| A | renal | 0.846332 | 0.796462–0.932439 | 0.135977 | 0.712003 | 0.705326–0.715663 | 0.010337 |
| A | metabolic | 0.863499 | 0.858651–0.873588 | 0.014937 | 0.818654 | 0.815623–0.823616 | 0.007992 |
| A | all organ pooled | 0.772360 | 0.769565–0.776766 | 0.007201 | 0.757969 | 0.756987–0.759251 | 0.002265 |
| B | cardiovascular | 0.798902 | 0.796894–0.800050 | 0.003156 | 0.797862 | 0.795241–0.800309 | 0.005068 |
| B | pulmonary | 0.818138 | 0.817066–0.818856 | 0.001790 | 0.814637 | 0.813975–0.815224 | 0.001248 |
| B | renal | 1.067043 | 1.018164–1.148013 | 0.129849 | 0.939610 | 0.931436–0.944142 | 0.012706 |
| B | metabolic | 0.859710 | 0.856209–0.864174 | 0.007965 | 0.831859 | 0.827041–0.836131 | 0.009090 |
| B | all organ pooled | 0.818781 | 0.816888–0.822623 | 0.005735 | 0.810142 | 0.808053–0.811263 | 0.003210 |

The persistence comparison uses the frozen file `results/v4/per_organ_v4.json`, fields `selected_seed_summary.persistence.A.renal.mean` and `selected_seed_summary.persistence.B.renal.mean`. Its SHA256 matches the archived reference copy cited in `renal_diagnosis.json`. Persistence is deterministic; its repeated seed entries are not independent fits. Frozen renal RMSEs are 0.762487 on A and 0.977049 on B. For context, the same file's `selected_seed_summary.physiograph_gru` renal mean fields are 0.813376 on A and 1.023438 on B; those are frozen admissible-edge runs, a different comparison from these no-edge arms.

The next table gives renal RMSE minus frozen persistence, with whether that arm is worse than persistence. Positive differences mean worse RMSE.

| Split | Arm | Seed 0: difference (worse?) | Seed 1: difference (worse?) | Seed 2: difference (worse?) | Seed 3: difference (worse?) | Mean difference (worse?) |
| --- | --- | --- | --- | --- | --- | --- |
| A | partitioned | +0.033975 (yes) | +0.169952 (yes) | +0.088894 (yes) | +0.042562 (yes) | +0.083846 (yes) |
| A | shared | -0.048390 (no) | -0.049562 (no) | -0.046823 (no) | -0.057160 (no) | -0.050484 (no) |
| B | partitioned | +0.041115 (yes) | +0.170963 (yes) | +0.104065 (yes) | +0.043831 (yes) | +0.089994 (yes) |
| B | shared | -0.035570 (no) | -0.035669 (no) | -0.032908 (no) | -0.045613 (no) | -0.037440 (no) |

The partitioned arm is worse than persistence in every seed and in the seed mean on both splits. The shared arm is below persistence in every seed and in the seed mean on both splits.

Shared projections add 18432 parameters. Counts are read from each run's `n_params` field; no model was instantiated to count parameters. All per-run RMSE values above are read directly from `run.json`: `<split>.organs.<organ>.RMSE` for organ scores and `<split>.pooled_masked_RMSE` for all-organ pooling. All requested fields were present, so no `errors_A.npz` or `errors_B.npz` recomputation was needed. Only subtraction, seed aggregation, ranges, and sign counts were calculated for this reading. `shared_input_summary.json` preserves unrounded values, exact source fields, aggregate source references, and the displayed decimal strings. Tables display six decimal places. Original input hashes are retained in the run records and distribution inventory; current file hashes are in the repository checksum list.

All file locators in these records are relative to the repository root. Original hashes identify the historical bytes before path and descriptive-label changes; use `manifests/distribution.json` and `SHA256SUMS` for current bytes. Locators under `runs/clinical/` and omitted checkpoint/error-array locators refer to outputs recreated by the documented experiment commands.
