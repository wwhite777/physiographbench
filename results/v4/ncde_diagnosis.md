Release interpretation: external re-inference was non-deterministic in the final
scientific check. External performance is therefore labelled **diverged** and
excluded from numerical model comparisons. The frozen diagnostic below describes
an earlier checkpoint probe; finite values in that probe do not establish
stable external inference. Its numerical observations are retained unchanged.

# Neural controlled differential equation (CDE) diagnosis

Checkpoint SHA-256: `32b77bdf040a23cc1a6a521b52da86efa08b597e0f16e6e30974c78b0723137f`.

CPU probe on 16 external B stays. Half are the worst windows from verified full-B frozen-checkpoint errors; the rest come from a fixed random subset. This purposive diagnostic subset does not estimate population performance. No optimizer or updates on B.

The frozen model puts a time **channel** from 0 to 1 in the path, but supplies no time **grid** to natural_cubic_coeffs/CubicSpline. The default spline grid therefore runs from 0 to C−1. For context length C=12, the fourth-order Runge–Kutta (RK4) step is 1/11 over [0,11], nominally 121 steps. The diagnostic comparison passes the same explicit [0,1] grid to both coefficient construction and spline evaluation, using the same 1/11 step (11 steps). A time channel and a spline parameter grid need not agree: a change of path parameter is valid for a CDE in continuous time. Holding this numerical step size fixed gives different integration resolution under the two parameterizations. The comparison does not by itself prove why a trained model diverged. Neither trace changes the frozen model or the registered tuning runs.

| Batch | Grid | Loss on B | Gradient norm | Nonfinite predictions | Nonfinite gradients | Status |
|---|---|---:|---:|---:|---:|---|
| 0 | frozen_default_index_grid | 17325.779296875 | 134262570064835.95 | 0 | 0 | complete |
| 0 | explicit_0_1_grid | 836454.75 | 13765123.812817112 | 0 | 0 | complete |
| 1 | frozen_default_index_grid | 0.762683093547821 | 4.0886941652215745 | 0 | 0 | complete |
| 1 | explicit_0_1_grid | 0.7826545238494873 | 4.811221643701593 | 0 | 0 | complete |

The already-computed full-B frozen-checkpoint evaluation covers 14824 eligible stays, with pooled masked RMSE 3.061958 and 0 nonfinite predictions. Per-window RMSE percentiles are `{"50": 0.753813624382019, "90": 1.1318669319152832, "95": 1.3019740581512451, "99": 1.8237580060958862, "100": 326.516357421875}`. These cached full-cohort errors motivate the worst-case probe; they are not evidence that the historical training trajectory has been recovered. The observed failure mode is a tail of large finite errors and gradients; the frozen evaluation did not reproduce nonfinite predictions.

The loss averages squared error over observed targets in A-train-normalized units. Gradients are measured before any clipping. The trace JSON includes the exact grid, solver step, maximum latent/prediction magnitudes, parameter-wise gradients, and counts of not-a-number (NaN) and infinite (Inf) values. A finite subset probe cannot establish numerical stability on all B stays or during full training. Historical training losses/gradients were not saved, so this is a frozen-checkpoint diagnosis rather than a reconstruction of its training trajectory.

Trace: `runs/clinical/ncde_trace.json` (SHA-256 `8500197aa27c4f913bf388d0dffc83d68f215719f4941bcbad3a53c6c423dda1`).
