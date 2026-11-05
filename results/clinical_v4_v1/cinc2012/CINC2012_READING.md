# CinC-2012: interpretation of the second open corpus
Source: TABLE_CINC2012.md / cinc2012_results.json (88 completed runs, 0 failures; pooled masked RMSE@12 re-derived from
per-stay error archives; mean ± sample sd over seeds 0–3). Two protocols: TRANSFER = the v4 CinC-2019 checkpoints (A-train normalisation) evaluated
on CinC-2012 set-a (3,989 eligible stays) and set-b (3,993; pooled 7,982); WITHIN = each model trained on set-a (3,390 train / 599 val) at its v4
selected configuration (paper hyper-parameters for the learned graphs) and tested on set-b (3,993). Caveat (cohort LINEAGE): the 2012 corpus
overlaps CinC-2019 set-A's hospital system; arterial SaO2 stands in for O2Sat; set-a/set-b are not asserted to be different hospitals.

## Result: both CinC-2019 orderings hold on the second corpus, with larger margins
| model | transfer pooled | within set-b |
|---|---|---|
| GRU-D | 0.8273 ± 0.0018 | 0.7684 ± 0.0018 |
| GRU | 0.8229 ± 0.0008 | 0.7712 ± 0.0016 |
| GRU-med | 0.8213 ± 0.0005 | 0.7681 ± 0.0011 |
| GRU-large | 0.8205 ± 0.0023 | 0.7524 ± 0.0012 |
| GraphGRU | 0.8296 ± 0.0024 | 0.7688 ± 0.0041 |
| ODE-RNN | 0.8343 ± 0.0034 | 0.7765 ± 0.0034 |
| PhysioGraph-GRU | 0.8529 ± 0.0020 | 0.8239 ± 0.0152 |
| PhysioGraph-SSM | 0.8738 ± 0.0039 | 0.8559 ± 0.0352 |
| Neural CDE | 0.9455 ± 0.0132 | 0.8888 ± 0.0066 |
| t-PatchGNN | 0.8142 ± 0.0005 | 0.7460 ± 0.0029 |
| GraFITi | 0.8192 ± 0.0059 | 0.7335 ± 0.0017 |
1. C1 reproduces: every recurrent baseline beats the organ-graph model on both protocols; the transfer gap GRU-D → PhysioGraph-GRU is +0.026 (vs
   +0.012 on CinC-2019 B) and the within gap +0.056; the organ-graph models are also the least seed-stable within CinC-2012 (sd 0.015 / 0.035 vs
   ≤ 0.004 for the GRU family). Per organ (within set-b) the organ graph loses most on renal (0.89 vs 0.69–0.76) and metabolic (1.00 vs 0.93–0.95).
2. C6 reproduces: the learned variable graphs are the best models on both protocols (transfer 0.814 / 0.819 vs GRU-family 0.821–0.827; within 0.746 /
   0.734 vs 0.752–0.771), with GraFITi's renal error within CinC-2012 (0.573) far below every recurrent model (≥ 0.646).
3. Within CinC-2012 the largest GRU is the best recurrent model (0.752) — the equal-budget configurations were selected on CinC-2019 A-val and not
   re-tuned here (the protocol says so); this does not change the ordering against the organ graph.
4. Neural CDE: finite but worst on both protocols (no divergence here); reported with its numbers.
