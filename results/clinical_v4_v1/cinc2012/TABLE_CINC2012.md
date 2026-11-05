# CinC-2012 transfer and within-corpus RMSE@12

Status: **complete**; scope: **full**; 88/88 runs.

Each seed's RMSE pools squared errors over observed target entries. Transfer pooled RMSE combines set-a and set-b numerators and denominators before taking the square root. The displayed mean ± sd is across seeds (sample sd, ddof=1). An absent sd is unavailable, not zero.

Transfer uses frozen CinC-2019 checkpoints and A-train normalization; both 2012 sets are test sets. Within-corpus uses 2012 A-train normalization and the fixed 2019-selected configurations. Its test_idx/testA is empty by design; only set-b is evaluated.

The 2012 sets are not asserted to be different hospitals. This second corpus overlaps the CinC-2019 set-A hospital system; arterial SaO2 substitutes for pulse-oximetry O2Sat. See the frozen cohort report for static mapping and unit qualifications.

## Transfer

Eligible-stay denominators (length ≥24 h): testA: 3,989/4,000 eligible/retained; 3,989 used; testB: 3,993/4,000 eligible/retained; 3,993 used; pooled: 7,982/8,000 eligible/retained; 7,982 used.

| Model | Seeds | testA RMSE@12 | testB RMSE@12 | pooled RMSE@12 |
|---|---:|---:|---:|---:|
| gru | 4/4 | 0.809928 ± 0.001027 | 0.835636 ± 0.000680 | 0.822878 ± 0.000769 |
| gru_med | 4/4 | 0.807752 ± 0.000639 | 0.834694 ± 0.000624 | 0.821328 ± 0.000529 |
| gru_large | 4/4 | 0.808936 ± 0.002922 | 0.831881 ± 0.001697 | 0.820485 ± 0.002297 |
| grud | 4/4 | 0.815062 ± 0.001509 | 0.839284 ± 0.002229 | 0.827257 ± 0.001849 |
| ncde | 4/4 | 0.924733 ± 0.008385 | 0.965724 ± 0.018508 | 0.945456 ± 0.013203 |
| odernn | 4/4 | 0.820954 ± 0.004287 | 0.847351 ± 0.002725 | 0.834252 ± 0.003420 |
| graphgru | 4/4 | 0.816743 ± 0.002576 | 0.842238 ± 0.002305 | 0.829584 ± 0.002422 |
| physiograph | 4/4 | 0.861336 ± 0.004414 | 0.886167 ± 0.003455 | 0.873835 ± 0.003922 |
| physiograph_gru | 4/4 | 0.837752 ± 0.002061 | 0.867743 ± 0.001898 | 0.852873 ± 0.001958 |
| tpatchgnn | 4/4 | 0.806734 ± 0.000393 | 0.821627 ± 0.001154 | 0.814212 ± 0.000546 |
| grafiti | 4/4 | 0.810792 ± 0.010473 | 0.827465 ± 0.003200 | 0.819179 ± 0.005943 |

### Transfer testA: per-organ pooled RMSE@12

Eligible-stay denominators (length ≥24 h): testA: 3,989/4,000 eligible/retained; 3,989 used; testB: 3,993/4,000 eligible/retained; 3,993 used; pooled: 7,982/8,000 eligible/retained; 7,982 used.

| Model | cardiovascular | pulmonary | renal | metabolic |
|---|---:|---:|---:|---:|
| gru | 0.770409 ± 0.000616 | 0.774987 ± 0.003662 | 0.812806 ± 0.003018 | 1.030601 ± 0.004704 |
| gru_med | 0.770110 ± 0.000470 | 0.770785 ± 0.001938 | 0.821534 ± 0.004133 | 1.018784 ± 0.002586 |
| gru_large | 0.773848 ± 0.003022 | 0.773397 ± 0.005762 | 0.790512 ± 0.005053 | 1.016274 ± 0.006226 |
| grud | 0.782741 ± 0.003146 | 0.758015 ± 0.005903 | 0.806309 ± 0.008982 | 1.022434 ± 0.004815 |
| ncde | 0.873019 ± 0.009511 | 0.916313 ± 0.003835 | 1.002423 ± 0.017452 | 1.163095 ± 0.014898 |
| odernn | 0.780736 ± 0.002374 | 0.787235 ± 0.001865 | 0.857310 ± 0.010158 | 1.035259 ± 0.015336 |
| graphgru | 0.772245 ± 0.000523 | 0.784717 ± 0.004627 | 0.839375 ± 0.015434 | 1.051679 ± 0.010833 |
| physiograph | 0.787261 ± 0.005275 | 0.828555 ± 0.001228 | 1.152210 ± 0.005825 | 1.139975 ± 0.008599 |
| physiograph_gru | 0.776745 ± 0.001015 | 0.825692 ± 0.002631 | 0.920539 ± 0.029674 | 1.112037 ± 0.004445 |
| tpatchgnn | 0.766108 ± 0.001568 | 0.749417 ± 0.004551 | 0.809429 ± 0.017664 | 1.046663 ± 0.008214 |
| grafiti | 0.775285 ± 0.001589 | 0.744566 ± 0.000615 | 0.773127 ± 0.000814 | 1.043765 ± 0.066517 |

### Transfer testB: per-organ pooled RMSE@12

Eligible-stay denominators (length ≥24 h): testA: 3,989/4,000 eligible/retained; 3,989 used; testB: 3,993/4,000 eligible/retained; 3,993 used; pooled: 7,982/8,000 eligible/retained; 7,982 used.

| Model | cardiovascular | pulmonary | renal | metabolic |
|---|---:|---:|---:|---:|
| gru | 0.775029 ± 0.000880 | 0.825547 ± 0.002985 | 0.675414 ± 0.003724 | 1.165756 ± 0.001502 |
| gru_med | 0.775207 ± 0.000548 | 0.822990 ± 0.000579 | 0.690993 ± 0.005488 | 1.158230 ± 0.001475 |
| gru_large | 0.778092 ± 0.002960 | 0.824678 ± 0.003745 | 0.653098 ± 0.007482 | 1.136794 ± 0.003665 |
| grud | 0.788142 ± 0.003760 | 0.811635 ± 0.006862 | 0.655953 ± 0.006628 | 1.148231 ± 0.001647 |
| ncde | 0.883191 ± 0.016456 | 0.965557 ± 0.009898 | 0.909690 ± 0.025088 | 1.360299 ± 0.045795 |
| odernn | 0.786226 ± 0.003583 | 0.837878 ± 0.004084 | 0.721859 ± 0.012835 | 1.172969 ± 0.002985 |
| graphgru | 0.776496 ± 0.001063 | 0.833101 ± 0.004383 | 0.698417 ± 0.016701 | 1.188612 ± 0.008707 |
| physiograph | 0.790318 ± 0.004912 | 0.882642 ± 0.001262 | 0.994128 ± 0.002463 | 1.286017 ± 0.003675 |
| physiograph_gru | 0.781262 ± 0.000974 | 0.879774 ± 0.003183 | 0.783808 ± 0.032141 | 1.267065 ± 0.002634 |
| tpatchgnn | 0.766570 ± 0.001092 | 0.800617 ± 0.002671 | 0.645735 ± 0.010602 | 1.139189 ± 0.006150 |
| grafiti | 0.774664 ± 0.000950 | 0.796919 ± 0.001695 | 0.623270 ± 0.001524 | 1.147769 ± 0.020527 |

### Transfer pooled: per-organ pooled RMSE@12

Eligible-stay denominators (length ≥24 h): testA: 3,989/4,000 eligible/retained; 3,989 used; testB: 3,993/4,000 eligible/retained; 3,993 used; pooled: 7,982/8,000 eligible/retained; 7,982 used.

| Model | cardiovascular | pulmonary | renal | metabolic |
|---|---:|---:|---:|---:|
| gru | 0.772723 ± 0.000698 | 0.800653 ± 0.003256 | 0.747180 ± 0.002806 | 1.099949 ± 0.002625 |
| gru_med | 0.772663 ± 0.000493 | 0.797301 ± 0.001173 | 0.758984 ± 0.004708 | 1.090420 ± 0.001489 |
| gru_large | 0.775974 ± 0.002962 | 0.799436 ± 0.004676 | 0.724978 ± 0.005307 | 1.077950 ± 0.003239 |
| grud | 0.785447 ± 0.003441 | 0.785269 ± 0.006303 | 0.734884 ± 0.007587 | 1.086868 ± 0.002665 |
| ncde | 0.878130 ± 0.012657 | 0.941253 ± 0.005808 | 0.957132 ± 0.020634 | 1.265154 ± 0.030914 |
| odernn | 0.783487 ± 0.002976 | 0.812938 ± 0.002966 | 0.792400 ± 0.010520 | 1.105975 ± 0.005737 |
| graphgru | 0.774374 ± 0.000697 | 0.809258 ± 0.004417 | 0.772026 ± 0.015814 | 1.121926 ± 0.009477 |
| physiograph | 0.788791 ± 0.005092 | 0.856011 ± 0.001097 | 1.075967 ± 0.004147 | 1.214862 ± 0.005973 |
| physiograph_gru | 0.779007 ± 0.000990 | 0.853147 ± 0.002863 | 0.854824 ± 0.030638 | 1.191722 ± 0.003082 |
| tpatchgnn | 0.766339 ± 0.001260 | 0.775427 ± 0.003469 | 0.732081 ± 0.012843 | 1.093703 ± 0.004999 |
| grafiti | 0.774974 ± 0.001257 | 0.771173 ± 0.001120 | 0.702103 ± 0.001113 | 1.097127 ± 0.036978 |

### Transfer: individual seeds

Eligible-stay denominators (length ≥24 h): testA: 3,989/4,000 eligible/retained; 3,989 used; testB: 3,993/4,000 eligible/retained; 3,993 used; pooled: 7,982/8,000 eligible/retained; 7,982 used.

| Model | Seed | Set | Used eligible stays | Observed target entries | RMSE@12 |
|---|---:|---|---:|---:|---:|
| gru | 0 | testA | 3989 | 242346 | 0.809498459 |
| gru | 1 | testA | 3989 | 242346 | 0.811052014 |
| gru | 2 | testA | 3989 | 242346 | 0.810439928 |
| gru | 3 | testA | 3989 | 242346 | 0.808722170 |
| gru | 0 | testB | 3993 | 242155 | 0.835184539 |
| gru | 1 | testB | 3993 | 242155 | 0.835634651 |
| gru | 2 | testB | 3993 | 242155 | 0.836597505 |
| gru | 3 | testB | 3993 | 242155 | 0.835128552 |
| gru | 0 | pooled | 7982 | 484501 | 0.822436720 |
| gru | 1 | pooled | 7982 | 484501 | 0.823430228 |
| gru | 2 | pooled | 7982 | 484501 | 0.823617411 |
| gru | 3 | pooled | 7982 | 484501 | 0.822026196 |
| gru_med | 0 | testA | 3989 | 242346 | 0.807355230 |
| gru_med | 1 | testA | 3989 | 242346 | 0.808379161 |
| gru_med | 2 | testA | 3989 | 242346 | 0.808206187 |
| gru_med | 3 | testA | 3989 | 242346 | 0.807068064 |
| gru_med | 0 | testB | 3993 | 242155 | 0.834834686 |
| gru_med | 1 | testB | 3993 | 242155 | 0.835514630 |
| gru_med | 2 | testB | 3993 | 242155 | 0.834137301 |
| gru_med | 3 | testB | 3993 | 242155 | 0.834289118 |
| gru_med | 0 | pooled | 7982 | 484501 | 0.821204491 |
| gru_med | 1 | pooled | 7982 | 484501 | 0.822053520 |
| gru_med | 2 | pooled | 7982 | 484501 | 0.821268984 |
| gru_med | 3 | pooled | 7982 | 484501 | 0.820786080 |
| gru_large | 0 | testA | 3989 | 242346 | 0.808745332 |
| gru_large | 1 | testA | 3989 | 242346 | 0.806694693 |
| gru_large | 2 | testA | 3989 | 242346 | 0.813118914 |
| gru_large | 3 | testA | 3989 | 242346 | 0.807185915 |
| gru_large | 0 | testB | 3993 | 242155 | 0.831512738 |
| gru_large | 1 | testB | 3993 | 242155 | 0.830550752 |
| gru_large | 2 | testB | 3993 | 242155 | 0.834356973 |
| gru_large | 3 | testB | 3993 | 242155 | 0.831105450 |
| gru_large | 0 | pooled | 7982 | 484501 | 0.820203549 |
| gru_large | 1 | pooled | 7982 | 484501 | 0.818704917 |
| gru_large | 2 | pooled | 7982 | 484501 | 0.823802202 |
| gru_large | 3 | pooled | 7982 | 484501 | 0.819228272 |
| grud | 0 | testA | 3989 | 242346 | 0.813687377 |
| grud | 1 | testA | 3989 | 242346 | 0.816007367 |
| grud | 2 | testA | 3989 | 242346 | 0.816682031 |
| grud | 3 | testA | 3989 | 242346 | 0.813869309 |
| grud | 0 | testB | 3993 | 242155 | 0.837528914 |
| grud | 1 | testB | 3993 | 242155 | 0.841556352 |
| grud | 2 | testB | 3993 | 242155 | 0.840832648 |
| grud | 3 | testB | 3993 | 242155 | 0.837219681 |
| grud | 0 | pooled | 7982 | 484501 | 0.825689503 |
| grud | 1 | pooled | 7982 | 484501 | 0.828875269 |
| grud | 2 | pooled | 7982 | 484501 | 0.828840546 |
| grud | 3 | pooled | 7982 | 484501 | 0.825622446 |
| ncde | 0 | testA | 3989 | 242346 | 0.935721043 |
| ncde | 1 | testA | 3989 | 242346 | 0.926823737 |
| ncde | 2 | testA | 3989 | 242346 | 0.918592668 |
| ncde | 3 | testA | 3989 | 242346 | 0.917795748 |
| ncde | 0 | testB | 3993 | 242155 | 0.993384096 |
| ncde | 1 | testB | 3993 | 242155 | 0.956582670 |
| ncde | 2 | testB | 3993 | 242155 | 0.958400752 |
| ncde | 3 | testB | 3993 | 242155 | 0.954529425 |
| ncde | 0 | pooled | 7982 | 484501 | 0.964972015 |
| ncde | 1 | pooled | 7982 | 484501 | 0.941814883 |
| ncde | 2 | pooled | 7982 | 484501 | 0.938699908 |
| ncde | 3 | pooled | 7982 | 484501 | 0.936335502 |
| odernn | 0 | testA | 3989 | 242346 | 0.817425689 |
| odernn | 1 | testA | 3989 | 242346 | 0.823659774 |
| odernn | 2 | testA | 3989 | 242346 | 0.825549345 |
| odernn | 3 | testA | 3989 | 242346 | 0.817179862 |
| odernn | 0 | testB | 3993 | 242155 | 0.844456928 |
| odernn | 1 | testB | 3993 | 242155 | 0.847857161 |
| odernn | 2 | testB | 3993 | 242155 | 0.850868341 |
| odernn | 3 | testB | 3993 | 242155 | 0.846220253 |
| odernn | 0 | pooled | 7982 | 484501 | 0.831045893 |
| odernn | 1 | pooled | 7982 | 484501 | 0.835841266 |
| odernn | 2 | pooled | 7982 | 484501 | 0.838299446 |
| odernn | 3 | pooled | 7982 | 484501 | 0.831821075 |
| graphgru | 0 | testA | 3989 | 242346 | 0.813317793 |
| graphgru | 1 | testA | 3989 | 242346 | 0.819385469 |
| graphgru | 2 | testA | 3989 | 242346 | 0.816469022 |
| graphgru | 3 | testA | 3989 | 242346 | 0.817799629 |
| graphgru | 0 | testB | 3993 | 242155 | 0.839202070 |
| graphgru | 1 | testB | 3993 | 242155 | 0.844810980 |
| graphgru | 2 | testB | 3993 | 242155 | 0.842494725 |
| graphgru | 3 | testB | 3993 | 242155 | 0.842445296 |
| graphgru | 0 | pooled | 7982 | 484501 | 0.826356183 |
| graphgru | 1 | pooled | 7982 | 484501 | 0.832190320 |
| graphgru | 2 | pooled | 7982 | 484501 | 0.829578810 |
| graphgru | 3 | pooled | 7982 | 484501 | 0.830209064 |
| physiograph | 0 | testA | 3989 | 242346 | 0.857018962 |
| physiograph | 1 | testA | 3989 | 242346 | 0.865158291 |
| physiograph | 2 | testA | 3989 | 242346 | 0.858043399 |
| physiograph | 3 | testA | 3989 | 242346 | 0.865124083 |
| physiograph | 0 | testB | 3993 | 242155 | 0.882392159 |
| physiograph | 1 | testB | 3993 | 242155 | 0.889011029 |
| physiograph | 2 | testB | 3993 | 242155 | 0.884077772 |
| physiograph | 3 | testB | 3993 | 242155 | 0.889185779 |
| physiograph | 0 | pooled | 7982 | 484501 | 0.869793086 |
| physiograph | 1 | pooled | 7982 | 484501 | 0.877161041 |
| physiograph | 2 | pooled | 7982 | 484501 | 0.871152714 |
| physiograph | 3 | pooled | 7982 | 484501 | 0.877232691 |
| physiograph_gru | 0 | testA | 3989 | 242346 | 0.836313344 |
| physiograph_gru | 1 | testA | 3989 | 242346 | 0.835875145 |
| physiograph_gru | 2 | testA | 3989 | 242346 | 0.838501351 |
| physiograph_gru | 3 | testA | 3989 | 242346 | 0.840318998 |
| physiograph_gru | 0 | testB | 3993 | 242155 | 0.865970498 |
| physiograph_gru | 1 | testB | 3993 | 242155 | 0.866259223 |
| physiograph_gru | 2 | testB | 3993 | 242155 | 0.869077763 |
| physiograph_gru | 3 | testB | 3993 | 242155 | 0.869663077 |
| physiograph_gru | 0 | pooled | 7982 | 484501 | 0.851265238 |
| physiograph_gru | 1 | pooled | 7982 | 484501 | 0.851196778 |
| physiograph_gru | 2 | pooled | 7982 | 484501 | 0.853920398 |
| physiograph_gru | 3 | pooled | 7982 | 484501 | 0.855111134 |
| tpatchgnn | 0 | testA | 3989 | 242346 | 0.806330128 |
| tpatchgnn | 1 | testA | 3989 | 242346 | 0.806861723 |
| tpatchgnn | 2 | testA | 3989 | 242346 | 0.806520641 |
| tpatchgnn | 3 | testA | 3989 | 242346 | 0.807221561 |
| tpatchgnn | 0 | testB | 3993 | 242155 | 0.821157005 |
| tpatchgnn | 1 | testB | 3993 | 242155 | 0.822825314 |
| tpatchgnn | 2 | testB | 3993 | 242155 | 0.822281467 |
| tpatchgnn | 3 | testB | 3993 | 242155 | 0.820243994 |
| tpatchgnn | 0 | pooled | 7982 | 484501 | 0.813774413 |
| tpatchgnn | 1 | pooled | 7982 | 484501 | 0.814879464 |
| tpatchgnn | 2 | pooled | 7982 | 484501 | 0.814436073 |
| tpatchgnn | 3 | pooled | 7982 | 484501 | 0.813756261 |
| grafiti | 0 | testA | 3989 | 242346 | 0.797020107 |
| grafiti | 1 | testA | 3989 | 242346 | 0.820798379 |
| grafiti | 2 | testA | 3989 | 242346 | 0.808664784 |
| grafiti | 3 | testA | 3989 | 242346 | 0.816683671 |
| grafiti | 0 | testB | 3993 | 242155 | 0.827236041 |
| grafiti | 1 | testB | 3993 | 242155 | 0.827522646 |
| grafiti | 2 | testB | 3993 | 242155 | 0.823636276 |
| grafiti | 3 | testB | 3993 | 242155 | 0.831465784 |
| grafiti | 0 | pooled | 7982 | 484501 | 0.812262633 |
| grafiti | 1 | pooled | 7982 | 484501 | 0.824166045 |
| grafiti | 2 | pooled | 7982 | 484501 | 0.816181908 |
| grafiti | 3 | pooled | 7982 | 484501 | 0.824104958 |

## Within

Eligible-stay denominators (length ≥24 h): train: 3,390/3,400 eligible/retained; 3,390 used; val: 599/600 eligible/retained; 599 used; testA: 0/0 eligible/retained; 0 used; testB: 3,993/4,000 eligible/retained; 3,993 used.

| Model | Seeds | testB RMSE@12 |
|---|---:|---:|
| gru | 4/4 | 0.771179 ± 0.001641 |
| gru_med | 4/4 | 0.768142 ± 0.001118 |
| gru_large | 4/4 | 0.752445 ± 0.001243 |
| grud | 4/4 | 0.768449 ± 0.001752 |
| ncde | 4/4 | 0.888790 ± 0.006581 |
| odernn | 4/4 | 0.776538 ± 0.003408 |
| graphgru | 4/4 | 0.768786 ± 0.004051 |
| physiograph | 4/4 | 0.855898 ± 0.035170 |
| physiograph_gru | 4/4 | 0.823867 ± 0.015241 |
| tpatchgnn | 4/4 | 0.746014 ± 0.002893 |
| grafiti | 4/4 | 0.733526 ± 0.001678 |

### Within testB: per-organ pooled RMSE@12

Eligible-stay denominators (length ≥24 h): train: 3,390/3,400 eligible/retained; 3,390 used; val: 599/600 eligible/retained; 599 used; testA: 0/0 eligible/retained; 0 used; testB: 3,993/4,000 eligible/retained; 3,993 used.

| Model | cardiovascular | pulmonary | renal | metabolic |
|---|---:|---:|---:|---:|
| gru | 0.724768 ± 0.000537 | 0.841504 ± 0.002339 | 0.762667 ± 0.012320 | 0.947967 ± 0.003745 |
| gru_med | 0.723282 ± 0.000380 | 0.830516 ± 0.004150 | 0.761157 ± 0.013234 | 0.943883 ± 0.001442 |
| gru_large | 0.725953 ± 0.001017 | 0.809637 ± 0.001477 | 0.645757 ± 0.002221 | 0.872814 ± 0.006181 |
| grud | 0.733427 ± 0.000565 | 0.820404 ± 0.006421 | 0.692397 ± 0.015575 | 0.925915 ± 0.008277 |
| ncde | 0.851111 ± 0.006813 | 0.975372 ± 0.009175 | 0.885056 ± 0.026907 | 1.012790 ± 0.013052 |
| odernn | 0.733742 ± 0.002972 | 0.841387 ± 0.006265 | 0.740709 ± 0.008446 | 0.948982 ± 0.003304 |
| graphgru | 0.725665 ± 0.001747 | 0.831049 ± 0.010609 | 0.739336 ± 0.030983 | 0.942715 ± 0.007859 |
| physiograph | 0.809288 ± 0.050614 | 0.940621 ± 0.031027 | 0.897032 ± 0.002474 | 1.008108 ± 0.002925 |
| physiograph_gru | 0.766435 ± 0.023490 | 0.924688 ± 0.016967 | 0.891734 ± 0.001175 | 1.004286 ± 0.002444 |
| tpatchgnn | 0.725223 ± 0.001585 | 0.779185 ± 0.003924 | 0.596542 ± 0.014534 | 0.868647 ± 0.007652 |
| grafiti | 0.725137 ± 0.001190 | 0.778340 ± 0.001650 | 0.573401 ± 0.001265 | 0.785641 ± 0.005223 |

### Within: individual seeds

Eligible-stay denominators (length ≥24 h): train: 3,390/3,400 eligible/retained; 3,390 used; val: 599/600 eligible/retained; 599 used; testA: 0/0 eligible/retained; 0 used; testB: 3,993/4,000 eligible/retained; 3,993 used.

| Model | Seed | Set | Used eligible stays | Observed target entries | RMSE@12 |
|---|---:|---|---:|---:|---:|
| gru | 0 | testB | 3993 | 242155 | 0.772349596 |
| gru | 1 | testB | 3993 | 242155 | 0.772690173 |
| gru | 2 | testB | 3993 | 242155 | 0.769193259 |
| gru | 3 | testB | 3993 | 242155 | 0.770484610 |
| gru_med | 0 | testB | 3993 | 242155 | 0.768416593 |
| gru_med | 1 | testB | 3993 | 242155 | 0.769579585 |
| gru_med | 2 | testB | 3993 | 242155 | 0.767022167 |
| gru_med | 3 | testB | 3993 | 242155 | 0.767549778 |
| gru_large | 0 | testB | 3993 | 242155 | 0.750862131 |
| gru_large | 1 | testB | 3993 | 242155 | 0.753639688 |
| gru_large | 2 | testB | 3993 | 242155 | 0.752078269 |
| gru_large | 3 | testB | 3993 | 242155 | 0.753198102 |
| grud | 0 | testB | 3993 | 242155 | 0.769300113 |
| grud | 1 | testB | 3993 | 242155 | 0.768954533 |
| grud | 2 | testB | 3993 | 242155 | 0.765859129 |
| grud | 3 | testB | 3993 | 242155 | 0.769683027 |
| ncde | 0 | testB | 3993 | 242155 | 0.886403976 |
| ncde | 1 | testB | 3993 | 242155 | 0.898426533 |
| ncde | 2 | testB | 3993 | 242155 | 0.883567188 |
| ncde | 3 | testB | 3993 | 242155 | 0.886764082 |
| odernn | 0 | testB | 3993 | 242155 | 0.774209114 |
| odernn | 1 | testB | 3993 | 242155 | 0.781212738 |
| odernn | 2 | testB | 3993 | 242155 | 0.773813663 |
| odernn | 3 | testB | 3993 | 242155 | 0.776916415 |
| graphgru | 0 | testB | 3993 | 242155 | 0.765976757 |
| graphgru | 1 | testB | 3993 | 242155 | 0.774573048 |
| graphgru | 2 | testB | 3993 | 242155 | 0.768605260 |
| graphgru | 3 | testB | 3993 | 242155 | 0.765989221 |
| physiograph | 0 | testB | 3993 | 242155 | 0.822724829 |
| physiograph | 1 | testB | 3993 | 242155 | 0.828300493 |
| physiograph | 2 | testB | 3993 | 242155 | 0.887305091 |
| physiograph | 3 | testB | 3993 | 242155 | 0.885263121 |
| physiograph_gru | 0 | testB | 3993 | 242155 | 0.818680240 |
| physiograph_gru | 1 | testB | 3993 | 242155 | 0.812316041 |
| physiograph_gru | 2 | testB | 3993 | 242155 | 0.846314914 |
| physiograph_gru | 3 | testB | 3993 | 242155 | 0.818156160 |
| tpatchgnn | 0 | testB | 3993 | 242155 | 0.748498943 |
| tpatchgnn | 1 | testB | 3993 | 242155 | 0.747567011 |
| tpatchgnn | 2 | testB | 3993 | 242155 | 0.741948601 |
| tpatchgnn | 3 | testB | 3993 | 242155 | 0.746042501 |
| grafiti | 0 | testB | 3993 | 242155 | 0.735791863 |
| grafiti | 1 | testB | 3993 | 242155 | 0.731742789 |
| grafiti | 2 | testB | 3993 | 242155 | 0.733184880 |
| grafiti | 3 | testB | 3993 | 242155 | 0.733385690 |
