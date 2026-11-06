#!/usr/bin/env python3
"""paired statistics: independent statistics from frozen records/arrays; no fitting or inference.

Run with Python, NumPy and SciPy already installed. All output stays beside this
script. Source JSONs and NPZs are read only. No project analysis code is imported.
"""
from __future__ import annotations

import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[2]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH

import argparse
import collections
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

import numpy as np
import scipy
from scipy import optimize, stats

HERE = Path(__file__).resolve().parent
PROJECT = RELEASE_ROOT
MATERIAL = PROJECT / "results"
SCRATCH = RELEASE_SCRATCH
SEEDS = (0, 1, 2, 3)
ORGANS = ("cardiovascular", "pulmonary", "renal", "metabolic")
VARIANTS = ("none", "admissible", "dense", "reversed", "random", "misspecified-1")



def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Evidence:
    def __init__(self):
        self.inputs = {}
        self.cache = {}

    def register(self, path):
        path = Path(path).resolve()
        rel = str(path.relative_to(PROJECT))
        if rel not in self.inputs:
            self.inputs[rel] = {"path": rel, "sha256": sha256(path), "bytes": path.stat().st_size}
        return rel

    def read(self, path):
        path = Path(path).resolve()
        self.register(path)
        if path not in self.cache:
            self.cache[path] = json.loads(path.read_text())
        return self.cache[path]

    def obs(self, path, field, value):
        return {"value": float(value), "source_file": self.register(path), "source_field": field}


E = Evidence()
ROWS = []
GROUPS = collections.OrderedDict()
CHECKS = []
BLOCKERS = []


def require(condition, description, **details):
    CHECKS.append({"check": description, "pass": bool(condition), **details})
    if not condition:
        raise AssertionError(description + ": " + str(details))


def nested(obj, field):
    for key in field.split("."):
        obj = obj[key]
    return obj


def mdd_multiplier(n=4):
    """Exact two-sided noncentral-t power inversion, plugging in observed paired SD."""
    critical = stats.t.ppf(.975, n - 1)

    def power(ncp):
        return stats.nct.cdf(-critical, n - 1, ncp) + stats.nct.sf(critical, n - 1, ncp)

    # Keep the bracket near the root: this SciPy build returns NaN for the tiny
    # negative tail at ncp=10 or 30, while ncp=8 already gives power > .99.
    ncp = optimize.brentq(lambda x: power(x) - .8, 0., 8., xtol=1e-13)
    return float(ncp / math.sqrt(n)), float(ncp), float(power(ncp))


MDD_FACTOR, MDD_NCP, MDD_POWER = mdd_multiplier()


def paired_summary(values, identity=False):
    a = np.asarray(values, dtype=np.float64)
    require(a.shape == (4,) and np.isfinite(a).all(), "four finite paired differences")
    mean = float(a.mean())
    sd = float(a.std(ddof=1))
    se = sd / 2.
    if sd > 0:
        t = mean / se
        p = float(2 * stats.t.sf(abs(t), 3))
        half = float(stats.t.ppf(.975, 3) * se)
        ci = [mean - half, mean + half]
        status = "complete"
    else:
        # An identity contrast supplies no estimated sampling variance or power.
        t, p, ci = None, None, [mean, mean]
        status = "identity_reference" if identity else "degenerate_zero_variance"
    return dict(n_pairs=4, seeds=list(SEEDS), mean_difference=mean, paired_sd_sample=sd,
                standard_error=se, ci95_paired_t=ci, df=3, t_statistic=t,
                p_two_sided_paired_t=p,
                sign_count={"negative": int((a < 0).sum()), "zero": int((a == 0).sum()),
                            "positive": int((a > 0).sum()), "denominator": 4},
                ci_excludes_zero=bool(ci[0] > 0 or ci[1] < 0) if sd > 0 else None,
                mdd_80pct_alpha05_n4=float(MDD_FACTOR * sd) if sd > 0 else None,
                status=status)


def add(group, title, label, lhs=None, rhs=None, differences=None, *, metric="pooled_RMSE",
        post_hoc=False, paper="", note="", identity=False):
    if group not in GROUPS:
        GROUPS[group] = {"title": title, "row_ids": [], "metric": metric}
    observations = []
    for seed in SEEDS:
        if differences is None:
            left, right = lhs[seed], rhs[seed]
            d = left["value"] - right["value"]
            observations.append({"seed": seed, "lhs": left, "rhs": right, "difference": d})
        else:
            d = differences[seed]["value"]
            observations.append({"seed": seed, "difference": d, "saved_difference": differences[seed]})
    rid = f"P{len(ROWS) + 1:04d}"
    row = dict(id=rid, group=group, contrast=label, metric=metric, post_hoc=post_hoc,
               paper_location=paper, note=note, observations=observations,
               **paired_summary([o["difference"] for o in observations], identity=identity))
    ROWS.append(row)
    GROUPS[group]["row_ids"].append(rid)
    return row


def run_series(paths, field):
    out = {}
    for p in paths:
        x = E.read(p)
        seed = int(x.get("seed", x.get("config", {}).get("seed", -1)))
        require(seed not in out, "unique seed in series", path=str(p), field=field)
        out[seed] = E.obs(p, field, nested(x, field))
    require(set(out) == set(SEEDS), "complete seed IDs", field=field)
    return out


def records_series(path, records, prefix, field):
    return {int(r["seed"]): E.obs(path, f"{prefix}[{i}].{field}", nested(r, field))
            for i, r in enumerate(records)}


def sim_contrasts():
    p = MATERIAL / "sim_grids_v1/h3_grid_with_controls.json"
    x = E.read(p)
    for i, c in enumerate(x["cells"]):
        for metric in ("macro_nrmse_fixed", "organ_nrmse_fixed.cardiovascular",
                       "organ_nrmse_fixed.renal", "organ_nrmse_fixed.metabolic"):
            d = {int(r["seed"]): E.obs(p, f"cells[{i}].paired_vs_none.per_seed[{j}].difference.{metric}",
                                         nested(r["difference"], metric))
                 for j, r in enumerate(c["paired_vs_none"]["per_seed"])}
            group = "sim_macro" if metric == "macro_nrmse_fixed" else "sim_organs"
            add(group, "Simulator: each variant minus none" if group == "sim_macro" else
                "Simulator: organ-specific fixed-range differences", 
                f"kappa={c['kappa']:g}; {c['variant']} - none" +
                (f"; {metric.split('.')[-1]}" if group == "sim_organs" else ""),
                differences=d, metric=metric, identity=c["variant"] == "none",
                paper="Fig. 1; Table 4 / tab:decomposition; Table 12 / tab:simall; app:decompositiondetail",
                note="control_gru_matched = mono-matched; control_gru = mono; split and fitting seeds coincide.")
    check = next(r for r in ROWS if r["group"] == "sim_macro" and
                 r["contrast"] == "kappa=1; control_gru_matched - none")
    require(check["sign_count"]["positive"] == 4 and .007 < check["p_two_sided_paired_t"] < .009,
            "reviewer mono-matched kappa=1 check", p_exact=check["p_two_sided_paired_t"], row=check["id"])


def clinical_variants():
    p = MATERIAL / "clinical_v4_v1/variant_ablation_v4.json"
    x = E.read(p)
    for model, variants in x["table"].items():
        for split in ("A", "B"):
            baseline = records_series(p, variants["none"]["runs"], f"table.{model}.none.runs",
                                      f"{split}.pooled_masked_RMSE")
            for variant in VARIANTS:
                c = variants[variant]
                lhs = records_series(p, c["runs"], f"table.{model}.{variant}.runs",
                                     f"{split}.pooled_masked_RMSE")
                add("clinical_variants", "Table 3: clinical variants minus none", 
                    f"{model}; {split}; {variant} - none", lhs, baseline, identity=variant == "none",
                    paper="Table 3 / tab:variants; sec:clinicalresults",
                    note="Partitioned input. Nonempty arms also retain coupling normalization; none bypasses it.")


def primary_series():
    p = MATERIAL / "clinical_v4_v1/per_organ_v4.json"
    x = E.read(p)
    models = list(x["table"]["seed0"])

    def get(model, split, organ=None, p=p, x=x):
        field = f"splits.{split}." + (f"organs.{organ}.RMSE" if organ else "pooled_masked_RMSE")
        return {s: E.obs(p, f"table.seed{s}.{model}.{field}", nested(x["table"][f"seed{s}"][model], field))
                for s in SEEDS}

    all_series = {(model, split): get(model, split) for model in models for split in ("A", "B")}
    # Follow explicit paper number-trace references for the two learned graphs.
    for model, subdir in (("tpatchgnn", "tpatchgnn"), ("grafiti", "grafiti_v3")):
        paths = sorted((MATERIAL / "learned_graph_baselines_v1" / subdir).glob(f"cinc_{model}_s*.json"))
        for split, field in (("A", "A_test.RMSE@12"), ("B", "B_external.RMSE@12")):
            all_series[model, split] = run_series(paths, field)
        models.append(model)
    for split in ("A", "B"):
        for baseline in ("grud", "physiograph_gru"):
            for model in models:
                if model == baseline:
                    continue
                # Preserve the stated orientation PG-GRU - GRU-D only once.
                if model == "grud" and baseline == "physiograph_gru":
                    continue
                add("clinical_headline", "Primary CinC-2019 pooled gaps", f"{split}; {model} - {baseline}",
                    all_series[model, split], all_series[baseline, split],
                    paper="Table 1 / tab:headline; sec:clinicalresults; sec:learnedresults; app:decompositiondetail",
                    note="Neural CDE B is a saved-record diagnostic excluded from primary ranking." if
                    split == "B" and "ncde" in (model, baseline) else
                    "Learned graphs use paper settings without the recurrent/organ selection grid." if
                    any(m in (model, baseline) for m in ("tpatchgnn", "grafiti")) else "")
        add("clinical_headline", "Primary CinC-2019 pooled gaps", f"{split}; grafiti - tpatchgnn",
            all_series["grafiti", split], all_series["tpatchgnn", split], paper="sec:learnedresults")
    for split in ("A", "B"):
        for model in ("physiograph_gru", "physiograph"):
            for baseline in ("grud", "persistence"):
                for organ in ORGANS:
                    add("clinical_organs", "Primary clinical organ gaps", f"{split}; {organ}; {model} - {baseline}",
                        get(model, split, organ), get(baseline, split, organ), metric=f"{organ}_RMSE",
                        paper="Table 5 / tab:perorgan; app:renalstrata; renal deficit discussion",
                        note="Persistence is one deterministic reference repeated against four fitted model seeds.")
    p = MATERIAL / "clinical_v4_v1/stats_v4.json"
    x = E.read(p)
    for split in ("A", "B"):
        for model in x["selected_model_seed_uncertainty"]:
            if model == "physiograph_gru":
                continue
            series = {}
            for m in ("physiograph_gru", model):
                base = f"selected_model_seed_uncertainty.{m}.{split}.per_seed"
                series[m] = {s: E.obs(p, f"{base}.seed{s}",
                                     x["selected_model_seed_uncertainty"][m][split]["per_seed"][f"seed{s}"])
                             for s in SEEDS}
            add("clinical_mean_stay", "Primary clinical mean-stay RMSE gaps across seeds",
                f"{split}; physiograph_gru - {model}", series["physiograph_gru"], series[model],
                metric="mean_stay_RMSE", paper="sec:clinicalresults; app:pairedexact",
                note="Across-seed paired t inference; distinct from within-checkpoint stay bootstrap/Wilcoxon.")
    return all_series, get


def shared_contrasts(primary_get):
    root17 = PROJECT / "diagnostics/renal_shared_input/artifacts/host"
    root20 = PROJECT / "diagnostics/shared_input_edges/artifacts/host"
    for split in ("A", "B"):
        for organ in (None, *ORGANS):
            field = f"{split}." + (f"organs.{organ}.RMSE" if organ else "pooled_masked_RMSE")
            shared = run_series(sorted((root17 / "shared").glob("seed*/run.json")), field)
            partitioned = run_series(sorted((root17 / "partitioned").glob("seed*/run.json")), field)
            add("shared_input", "Table 14: shared minus partitioned input (post-hoc)",
                f"{split}; {organ or 'pooled'}; shared - partitioned", shared, partitioned,
                metric=f"{organ or 'pooled'}_RMSE", post_hoc=True,
                paper="Table 14 / tab:sharedinput; app:sharedinput; sec:clinicalresults",
                note="Shared projections add 18,432 parameters; fixed partitioned-selected settings, no retuning.")
            if organ == "renal":
                for arm, series in (("shared", shared), ("partitioned", partitioned)):
                    add("shared_input", "Table 14: shared minus partitioned input (post-hoc)",
                        f"{split}; renal; {arm} - persistence", series, primary_get("persistence", split, "renal"),
                        metric="renal_RMSE", post_hoc=True, paper="Table 14 / tab:sharedinput",
                        note="Deterministic frozen persistence reference, repeated for fitted model seed pairs.")
            baseline = run_series(sorted((root20 / "none").glob("seed*/run.json")), field)
            for variant in VARIANTS:
                lhs = run_series(sorted((root20 / variant).glob("seed*/run.json")), field)
                add("shared_edges", "Table 15: shared-input variants minus none (post-hoc)",
                    f"{split}; {organ or 'pooled'}; {variant} - none", lhs, baseline,
                    metric=f"{organ or 'pooled'}_RMSE", post_hoc=True, identity=variant == "none",
                    paper="Table 15 / tab:sharedinputedges; app:sharedinputedgesummary",
                    note="Fixed settings selected on partitioned input; parameters differ by edge set; no retuning.")


def horizon_contrasts():
    p = MATERIAL / "clinical_v4_v1/horizon_table_v4.json"
    x = E.read(p)
    gaps = {}
    for design, models in x["table"].items():
        for split in ("A", "B"):
            series = {m: records_series(p, v["runs"], f"table.{design}.{m}.runs", f"{split}.pooled_masked_RMSE")
                      for m, v in models.items()}
            for model in models:
                if model == "grud":
                    continue
                row = add("horizons", "Common-cohort horizon gaps versus GRU-D",
                          f"{design}; {split}; {model} - grud", series[model], series["grud"],
                          paper="Tables 9-11 / tab:horizon0,18,36; Fig. 6; fixed-context horizon paragraph",
                          note="Common >=48-hour eligible cohort; separate fits for each design, no retuning.")
                if model == "physiograph_gru":
                    gaps[design, split] = row
    for first, last in (("C12_K6", "C12_K12"), ("C12_K12", "C12_K24"),
                        ("C12_K6", "C12_K24"), ("C24_K12", "C24_K24")):
        for split in ("A", "B"):
            d = {}
            for seed, left, right in zip(SEEDS, gaps[last, split]["observations"], gaps[first, split]["observations"]):
                d[seed] = {"value": left["difference"] - right["difference"],
                           "source_file": E.register(p),
                           "source_field": f"difference of gaps: {gaps[last, split]['id']}[{seed}] - {gaps[first, split]['id']}[{seed}]"}
            add("horizon_changes", "Change in the PhysioGraph-GRU minus GRU-D horizon gap",
                f"{split}; {last} gap - {first} gap", differences=d,
                paper="sec:learnedresults; fixed-context horizon paragraph; Fig. 6",
                note="Negative difference means narrowing of the gap; matched seed labels, different fitted designs.")


def cinc_contrasts(primary):
    p = MATERIAL / "clinical_v4_v1/cinc2012/cinc2012_results.json"
    x = E.read(p)
    cache = {}
    for protocol, pr in x["protocols"].items():
        models = pr["models"]
        for split in next(iter(models.values()))["splits"]:
            for model in models:
                base = f"protocols.{protocol}.models.{model}.splits.{split}.per_seed"
                per_seed = models[model]["splits"][split]["per_seed"]
                cache[protocol, split, model] = {
                    int(s): E.obs(p, f"{base}.{s}.pooled_masked_RMSE", v["pooled_masked_RMSE"])
                    for s, v in per_seed.items()}
            pairs = [(m, "grud") for m in models if m != "grud"]
            pairs += [("physiograph_gru", m) for m in models if m not in ("physiograph_gru", "grud")]
            recurrent = min(("gru", "gru_med", "gru_large", "grud"),
                            key=lambda m: models[m]["splits"][split]["RMSE"]["mean"])
            pairs += [(g, recurrent) for g in ("tpatchgnn", "grafiti") if (g, recurrent) not in pairs]
            pairs += [("grafiti", "tpatchgnn")]
            for a, b in pairs:
                add("cinc2012", "CinC-2012 model gaps within each protocol and split",
                    f"{protocol}; {split}; {a} - {b}", cache[protocol, split, a], cache[protocol, split, b],
                    paper="Table 2 / tab:cinc2012; sec:cinc2012results; second-corpus comparison paragraph",
                    note="Transfer uses frozen CinC-2019 models; within uses set-a fits without retuning. Seed labels align.")
    for model in x["protocols"]["within"]["models"]:
        add("cinc_protocol", "CinC-2012: within minus transfer on the common set-b test records",
            f"testB; {model}; within - transfer", cache["within", "testB", model],
            cache["transfer", "testB", model], paper="Table 2 / tab:cinc2012",
            note="Exploratory: same test identities and seed labels, but training corpus and normalization change; not a pure protocol effect.")
    # The paper compares margins across corpora; retain these as explicit derived contrasts.
    comparisons = [
        ("PG-GRU minus GRU-D margin: CinC-2012 transfer pooled - CinC-2019 B",
         ("physiograph_gru", "grud"), ("physiograph_gru", "grud")),
        ("best learned minus best recurrent margin: CinC-2012 transfer pooled - CinC-2019 B",
         ("tpatchgnn", "gru_large"), ("grafiti", "grud"))]
    for label, pair12, pair19 in comparisons:
        differences = {}
        for seed in SEEDS:
            a, b = (cache["transfer", "pooled", m][seed] for m in pair12)
            c, d = (primary[m, "B"][seed] for m in pair19)
            differences[seed] = {"value": a["value"] - b["value"] - c["value"] + d["value"],
                                 "source_file": E.register(p), "source_field": "derived cross-corpus margin",
                                 "terms": [a, b, c, d]}
        add("cross_corpus", "Cross-corpus differences in stated model margins", label,
            differences=differences, paper="sec:cinc2012results; second-corpus comparison paragraph",
            note="Exploratory paired seed-label contrast across different test populations; shared transferred checkpoints where applicable. Best-model labels use the observed four-seed pooled means and do not establish statistically reliable ranking.")


def holm_families():
    p = MATERIAL / "clinical_v4_v1/stats_v4.json"
    x = E.read(p)
    families = []
    for seed, splits in x["sampling_uncertainty"].items():
        for split, models in splits.items():
            members = []
            for model, rec in models.items():
                if rec["status"] == "complete":
                    b = f"sampling_uncertainty.{seed}.{split}.{model}"
                    w = rec["wilcoxon_window_RMSE"]
                    members.append(dict(comparator=model, contrast=f"physiograph_gru - {model}",
                                        raw_p=w["p_value"], saved_adjusted_p=w["p_holm_within_checkpoint_split"],
                                        source_file=E.register(p), source_field=f"{b}.wilcoxon_window_RMSE",
                                        n_evaluable_stays=rec["n_stays"], estimand=rec["estimand"]))
            ranked = sorted(members, key=lambda z: (z["raw_p"], z["comparator"]))
            running = 0.
            for rank, m in enumerate(ranked, 1):
                running = max(running, min(1., m["raw_p"] * (len(ranked) - rank + 1)))
                m["rank"] = rank
                m["adjusted_p_recomputed"] = running
                require(math.isclose(running, m["saved_adjusted_p"], rel_tol=1e-14, abs_tol=0.),
                        "Holm correction reproduces frozen value", seed=seed, split=split, model=m["comparator"])
            families.append(dict(id=f"Holm_{seed}_{split}", seed=seed, split=split, family_size=len(members),
                                 reference="physiograph_gru", test="two-sided Wilcoxon signed-rank on paired stay RMSE differences",
                                 members=ranked, adjustment_scope="one checkpoint pair-reference family per seed and split; no pooling across seeds or splits"))
    return families


def bootstrap_vs_grud(draws=2000):
    """Paired eligible-stay resampling; re-pool SSE/count on every draw."""
    root = PROJECT / "results/v4/selected"
    out = []
    for seed in SEEDS:
        for split in ("A", "B"):
            paths = sorted(root.glob(f"*/seed{seed}/errors_{split}.npz"))
            arrays = {}
            for p in paths:
                E.register(p)
                with np.load(p, allow_pickle=False) as z:
                    arrays[p.parent.parent.name] = {k: z[k].copy() for k in ("stay_index", "sse", "count", "nonfinite")}
            ref = arrays["grud"]
            valid = ref["count"] > 0
            n = int(valid.sum())
            models = sorted(arrays)
            for model in models:
                ar = arrays[model]
                require(np.array_equal(ar["stay_index"], ref["stay_index"]) and np.array_equal(ar["count"], ref["count"]),
                        "bootstrap stay identity and count alignment", seed=seed, split=split, model=model)
                require(np.isfinite(ar["sse"]).all() and not ar["nonfinite"].any(),
                        "no silent nonfinite-error exclusions", seed=seed, split=split, model=model)
            sse = np.column_stack([arrays[m]["sse"][valid] for m in models]).astype(np.float64)
            count = ref["count"][valid].astype(np.float64)
            model_index = {m: i for i, m in enumerate(models)}
            g = model_index["grud"]
            stay_rmse = np.sqrt(sse / count[:, None])
            pool = np.sqrt(sse.sum(axis=0) / count.sum())
            point = pool - pool[g]
            stay_point = (stay_rmse - stay_rmse[:, g, None]).mean(axis=0)
            boot_pool = np.empty((draws, len(models)), dtype=np.float64)
            boot_stay = np.empty_like(boot_pool)
            rng = np.random.default_rng(0)
            # Batch only indexing; RNG draws match one n-stay resample at a time.
            for start in range(0, draws, 32):
                stop = min(start + 32, draws)
                indices = rng.integers(0, n, size=(stop - start, n))
                denom = count[indices].sum(axis=1)
                re_pool = np.sqrt(sse[indices].sum(axis=1) / denom[:, None])
                boot_pool[start:stop] = re_pool - re_pool[:, g, None]
                re_stay = stay_rmse[indices].mean(axis=1)
                boot_stay[start:stop] = re_stay - re_stay[:, g, None]
            for model in models:
                if model == "grud":
                    continue
                j = model_index[model]
                paths_pair = [root / model / f"seed{seed}/errors_{split}.npz", root / "grud" / f"seed{seed}/errors_{split}.npz"]
                runs_pair = [E.read(p.parent / "run.json") for p in paths_pair]
                saved_gap = runs_pair[0][split]["pooled_masked_RMSE"] - runs_pair[1][split]["pooled_masked_RMSE"]
                tolerance = 2e-6  # JSON pools and saved per-stay float32 reductions need not be bit-identical.
                # Large NCDE values use a relative tolerance as well, but remain excluded diagnostics.
                require(math.isclose(float(point[j]), saved_gap, rel_tol=2e-6, abs_tol=tolerance),
                        "array re-pooling agrees with frozen pooled gap", seed=seed, split=split, model=model,
                        saved_gap=saved_gap, array_gap=float(point[j]))
                out.append(dict(id=f"B_{model}_s{seed}_{split}", model=model, comparator="grud", seed=seed, split=split,
                                gap_direction="model minus GRU-D", draws=draws, rng="numpy.default_rng(0)",
                                unit="stay (one window per stay)", paired=True, interval="percentile, numpy linear quantile",
                                confidence=.95, n_eligible_stays=len(valid), n_resampled_evaluable_stays=n,
                                n_zero_target_stays_excluded=int((~valid).sum()),
                                observed_target_entries=int(count.sum()),
                                pooled_denominator="sum of observed target entries in the resampled stays, counting duplicates",
                                pooled_point_from_saved_arrays=float(point[j]), pooled_saved_json_gap=saved_gap,
                                array_minus_json_gap=float(point[j] - saved_gap),
                                pooled_ci95=np.quantile(boot_pool[:, j], [.025, .975]).tolist(),
                                mean_stay_point_from_saved_arrays=float(stay_point[j]),
                                mean_stay_ci95=np.quantile(boot_stay[:, j], [.025, .975]).tolist(),
                                source_files=[E.register(p) for p in paths_pair],
                                source_fields=["stay_index", "sse", "count", "nonfinite"],
                                frozen_json_source_files=[E.register(p.parent / "run.json") for p in paths_pair],
                                frozen_json_source_fields=[f"{split}.pooled_masked_RMSE"],
                                diagnostic_excluded_from_primary_ranking=model == "ncde" and split == "B",
                                limitation="Conditional on fitted checkpoints. No seed resampling/refitting, hospital uncertainty or person-level admission clustering."))
            print(f"bootstrap seed={seed} split={split}: {len(models)-1} model gaps, {draws} draws, n={n}", flush=True)
    return out


def h5_runs():
    root = PROJECT / "sim/artifacts/full_grid/runs"
    paths = sorted(root.glob("h5_*.json"))
    index = {}
    for p in paths:
        x = E.read(p)
        c = x["config"]
        key = (x["cf_protocol"], c["confound"], c["sigma"], c["model"], c["seed"])
        require(key not in index, "unique H5 run key", key=key)
        index[key] = (p, x)
    return index


def cf_contrasts(index):
    h = E.read(MATERIAL / "sim_grids_v1/h5_grid.json")
    cells = [c for c in h["cells"] if c["cf_protocol"] == "shared"]
    policies = sorted(set((c["confound"], c["sigma"]) for c in cells))
    for c, sigma in policies:
        for metric in ("direction_accuracy.cell_mean", "macro_nrmse_fixed"):
            series = {}
            for model in ("crn_lite", "control_gru"):
                series[model] = {s: E.obs(index["shared", c, sigma, model, s][0], f"metrics.{metric}",
                                         nested(index["shared", c, sigma, model, s][1]["metrics"], metric))
                                 for s in SEEDS}
            add("cf_lite", "CRN-lite minus Control-GRU on the shared-history policy grid",
                f"c={c:g}; sigma={sigma:g}; {metric}; crn_lite - control_gru", series["crn_lite"],
                series["control_gru"], metric=metric, paper="app:crncomparisonunits; app:crnmaincomparison; app:crnzerotarget",
                note="Descriptive paired contrast; constant-zero auxiliary target supplies no balancing test.")
    root = MATERIAL / "learned_graph_baselines_v1/crn_v2_lambda_sweep"
    sweep = collections.defaultdict(dict)
    for p in sorted(root.glob("*.json")):
        x = E.read(p)
        c = x["config"]
        key = (c["confound"], c["sigma"], c["lamb"], c["epochs"])
        sweep[key][c["seed"]] = (p, x)
    for (c, sigma, lamb, epochs), runs in sorted(sweep.items()):
        for metric in ("direction_accuracy.cell_mean", "macro_nrmse_fixed"):
            lhs = {s: E.obs(runs[s][0], f"metrics.{metric}", nested(runs[s][1]["metrics"], metric)) for s in SEEDS}
            rhs = {s: E.obs(index["shared", c, sigma, "control_gru", s][0], f"metrics.{metric}",
                           nested(index["shared", c, sigma, "control_gru", s][1]["metrics"], metric)) for s in SEEDS}
            add("cf_crn", "Continuous-dose CRN sweep minus Control-GRU",
                f"c={c:g}; sigma={sigma:g}; lambda={lamb:g}; epochs={epochs}; {metric}", lhs, rhs,
                metric=metric, paper="Table 13 / tab:crnsweep; app:crnmaincomparison; app:directionscoring",
                note="Different estimator; randomised eventual dose does not identify the earlier treatment start.")


def direction_decomposition(index):
    p = MATERIAL / "sim_grids_v1/h5_grid.json"
    h = E.read(p)
    result = []
    scanned = PROJECT / "sim"
    extensions = dict(collections.Counter(f.suffix for f in scanned.rglob("*") if f.is_file()))
    # The verifier did save a small smoke prediction array, but it has four test
    # patients, not the 120-patient full-grid runs. Do not substitute it.
    smoke_path = PROJECT / "historical_sources/verify/artifacts/h5_shared_predictions.npz"
    with np.load(smoke_path, allow_pickle=False) as z:
        smoke_shape = list(z["cf_prediction"].shape)
    E.register(smoke_path)
    for ci, cell in enumerate(h["cells"]):
        per_seed = []
        for seed in SEEDS:
            key = (cell["cf_protocol"], cell["confound"], cell["sigma"], cell["model"], seed)
            run_path, run = index[key]
            score = run["metrics"]["direction_accuracy"]
            data_path = Path(run["dataset"]["path"])
            data_key = E.register(data_path)
            require(E.inputs[data_key]["sha256"] == run["dataset"]["sha256"],
                    "H5 target archive matches run-record hash", run=str(run_path))
            with np.load(data_path, allow_pickle=False) as z:
                truth = z["counterfactual_target"][run["dataset"]["test_indices"]].astype(np.float64)
                channels = z["channels"].tolist()
            delta = np.diff(truth, axis=1)
            total = delta.size
            nzero = int((delta == 0).sum())
            ncorrect = round(score["cell_mean"] * total)
            npredzero = round(score["predicted_zero_change_fraction"] * total)
            require(total == score["n_cells"] and math.isclose(nzero / total, score["true_zero_change_fraction"], abs_tol=1e-14),
                    "H5 saved target denominators reproduce JSON", run=str(run_path))
            require(abs(ncorrect / total - score["cell_mean"]) < 1e-14,
                    "H5 integer sign numerator recovered exactly", run=str(run_path))
            # Intersection of true-zero and predicted-zero cells cannot be recovered from marginals.
            zlo, zhi = max(0, npredzero - (total - nzero)), min(npredzero, nzero)
            zero_correct = zlo if zlo == zhi else None
            nfirst = delta[:, :, :1, :].size
            npost = total - nfirst
            # Bound correct first-target cells using each channel's total correct and truth zeros.
            # Zero cells can match only predicted zeros. No assumption about CVP's first-step prediction.
            nonzero_first_lo = 0
            nonzero_first_hi = 0
            channel_counts = []
            for j, ch in enumerate(channels):
                all_n = delta[..., j].size
                first_n = delta[:, :, 0, j].size
                correct_j = round(score["per_channel"][ch] * all_n)
                first_zero = int((delta[:, :, 0, j] == 0).sum())
                first_nonzero = first_n - first_zero
                post_true_zero = int((delta[:, :, 1:, j] == 0).sum())
                # Minimal possible correct first nonzero after allocating all post and zero-first matches.
                lo = max(0, correct_j - (all_n - first_n) - min(npredzero, first_zero))
                hi = min(first_nonzero, correct_j)
                nonzero_first_lo += lo
                nonzero_first_hi += hi
                channel_counts.append(dict(channel=ch, n_all=all_n, n_first=first_n,
                                           n_true_zero_first=first_zero, n_true_zero_post=post_true_zero,
                                           n_correct_all=correct_j))
            first_zero_total = int((delta[:, :, :1, :] == 0).sum())
            first_correct_lo = nonzero_first_lo + max(0, zlo - int((delta[:, :, 1:, :] == 0).sum()))
            first_correct_hi = nonzero_first_hi + min(zhi, first_zero_total)
            post_correct_bounds = [max(0, ncorrect - first_correct_hi), min(npost, ncorrect - first_correct_lo)]
            post_exact = post_correct_bounds[0] if post_correct_bounds[0] == post_correct_bounds[1] else None
            effect_rows = []
            # Sensitivity definitions are explicit; they are not historical thresholds.
            # Within-channel scale uses the saved legacy reference max-min, so mixed units are not combined.
            ref_path = Path(run["normalization"]["reference_path"])
            ref_key = E.register(ref_path)
            require(E.inputs[ref_key]["sha256"] == run["normalization"]["reference_sha256"],
                    "H5 range reference matches run-record hash", run=str(run_path))
            with np.load(ref_path, allow_pickle=False) as z:
                reference = z["counterfactual"].astype(np.float64)
            channel_range = np.ptp(reference, axis=(0, 1, 2))
            for tolerance in (1e-6, 1e-4, 1e-3):
                threshold = tolerance * channel_range
                eligible = np.abs(delta[:, :, 1:, :]) > threshold
                effect_rows.append(dict(tolerance_fraction_of_reference_channel_range=tolerance,
                                        channel_thresholds=dict(zip(channels, threshold.tolist())),
                                        denominator_post_nontrivial_effect=int(eligible.sum()),
                                        numerator=None, accuracy=None, status="BLOCKED_MISSING_PER_CELL_PREDICTIONS",
                                        rule="Exclude first target; retain |true adjacent-dose effect| > tolerance * channel range; exact sign match on retained cells.",
                                        range_source_file=E.register(ref_path), range_source_field="counterfactual: channel max-minus-min over all patients, doses, times"))
            per_seed.append(dict(seed=seed, n_all=total, n_correct_all=ncorrect,
                                 all_accuracy=score["cell_mean"], n_predicted_exact_zero=npredzero,
                                 n_true_exact_zero=nzero, n_correct_zero_exact=zero_correct,
                                 n_correct_zero_bounds=[zlo, zhi],
                                 zero_effect_accuracy=(zero_correct / nzero if nzero and zero_correct is not None else None),
                                 zero_effect_accuracy_bounds=([zlo / nzero, zhi / nzero] if nzero else None),
                                 n_first_target=nfirst, n_post_first_target=npost,
                                 n_true_zero_post_first=int((delta[:, :, 1:, :] == 0).sum()),
                                 n_correct_post_first=post_exact, n_correct_post_first_bounds=post_correct_bounds,
                                 post_first_accuracy=(post_exact / npost if post_exact is not None else None),
                                 post_first_accuracy_bounds=[v / npost for v in post_correct_bounds],
                                 channel_counts=channel_counts, effect_tolerance_variants=effect_rows,
                                 source_file=E.register(run_path), source_field="metrics.direction_accuracy",
                                 truth_source_file=E.register(data_path), truth_source_field="counterfactual_target[dataset.test_indices]; diff over adjacent doses"))
        mean = float(np.mean([v["all_accuracy"] for v in per_seed]))
        require(math.isclose(mean, cell["metrics"]["direction_accuracy"]["cell_mean"]["mean"], abs_tol=2e-15),
                "per-run H5 direction means match frozen aggregate", cell=ci)
        result.append(dict(cell_index=ci, cf_protocol=cell["cf_protocol"], c=cell["confound"], sigma=cell["sigma"],
                           model=cell["model"], seeds=list(SEEDS), aggregate_source_file=E.register(p),
                           aggregate_source_field=f"cells[{ci}].metrics.direction_accuracy", per_seed=per_seed,
                           mean_all_accuracy=mean,
                           mean_post_first_accuracy_bounds=np.mean([v["post_first_accuracy_bounds"] for v in per_seed], axis=0).tolist(),
                           mean_zero_accuracy=(float(np.mean([v["zero_effect_accuracy"] for v in per_seed]))
                                               if all(v["zero_effect_accuracy"] is not None for v in per_seed) else None),
                           status="PARTIAL_IDENTIFICATION_ONLY"))
    BLOCKERS.append(dict(id="DIRECTION_ARRAYS", status="BLOCKED", scope="exact post-first-target and effect-tolerance direction accuracies",
                         reason="h5_grid.json and original per-run JSONs save marginal sign accuracies/zero fractions, not the per-cell predictions or sign matches. Original H5 task tree contains no saved prediction arrays or checkpoints; target NPZs alone cannot recover predictions. Re-fitting/re-inference is prohibited by this card.",
                         inspected_directory=str(scanned.relative_to(PROJECT)), observed_file_extensions=extensions,
                         excluded_prediction_candidate=dict(source_file=E.register(smoke_path),
                                                            source_field="cf_prediction", shape=smoke_shape,
                                                            reason="4-patient smoke test, not a 120-patient original full-grid run"),
                         impact="All 108 model/policy cells have denominator rows and rigorous aggregate bounds; missing accuracies are null, never estimated from marginal scores.",
                         tolerance_choice="No numerical effect tolerance specified by card. Three explicit channel-range sensitivity definitions are provided; none is represented as a preregistered rule."))
    return result


def number(x):
    if x is None:
        return "NA"
    if x == 0:
        return "0"
    return f"{x:.9g}"


def source_text(row):
    o = row["observations"][0]
    records = [o["saved_difference"]] if "saved_difference" in o else [o["lhs"], o["rhs"]]
    return " ; ".join(f"`{r['source_file']} :: {r['source_field']}`" for r in records)


def make_markdown(data):
    lines = ["# Paired statistics v5 — paired statistics", "", 
             "Status: **PARTIAL / direction decomposition BLOCKED by missing original per-cell predictions**. "
             "The paired seed analyses, pooled-gap bootstraps and historical Holm families are computed. "
             "No new fitting or model inference was performed. Tables 14/15 and their tests remain post-hoc.", "",
             "The exact machine-readable values, all four seed observations, source file/field for every observation, "
             "and SHA-256 input catalog are in `paired_stats_v5.json`. Markdown displays nine significant digits; "
             "JSON retains binary64 values. `Pxxxx` identifies an exact JSON `paired_contrasts` row. "
             "Source cells below show seed 0; the JSON supplies the corresponding seed 1–3 fields and all hashes.", "",
             "## Definitions and scope", "",
             "A paired difference is the left score minus the right score at the same recorded training seed (0–3). "
             "Negative RMSE/NRMSE differences favor the left model; positive direction-accuracy differences favor the left model. "
             "The paired sample standard deviation is computed from the four differences, with divisor 3. "
             "The 95% paired t confidence interval (CI) is mean ± t(0.975,3) × paired SD / 2; p-values are two-sided. "
             "They rely on the model of independent, normally distributed seed differences. Simulation seeds also change the patient split. "
             "Clinical seeds share fixed cohorts, so seed inference conditions on those cohorts and does not establish population or hospital generalization.", "",
             f"Minimum detectable difference (MDD) is a plug-in sensitivity calculation: for n=4 pairs, alpha=0.05 (two-sided), "
             f"80% power, the exact noncentral-t inversion gives MDD = {number(MDD_FACTOR)} × paired SD "
             f"(noncentrality {number(MDD_NCP)}). It treats the observed paired SD as a planning population SD; "
             "with four pairs this estimate is uncertain. It is not observed power, an equivalence margin or evidence that a null effect is absent. "
             "Every ordinary null row has an MDD. Identity references have zero variance and no inferential test/MDD (NA).", "",
             "The seed t tests below are newly computed, exploratory and unadjusted. The historical Holm families are "
             "the stay-level Wilcoxon families explicitly reconstructed later; they do not adjust this new collection of seed t tests. "
             "A raw CI excluding zero is therefore not a familywise significance claim. Extra organ/model comparisons are included "
             "to make all stated orderings inspectable. Comparisons across corpora/designs preserve common seed labels but change fitted models or populations as stated.", "",
             "## paper contrast coverage", "",
             "| paper statement/table | Evidence rows |", "|---|---|"]
    for g, info in GROUPS.items():
        lines.append(f"| {info['title']} | {', '.join(info['row_ids'])} |")
    check = next(r for r in ROWS if r["group"] == "sim_macro" and r["contrast"] == "kappa=1; control_gru_matched - none")
    lines += ["", f"Reviewer check ({check['id']}): mono-matched minus none at kappa=1 is positive in 4/4 seeds; "
              f"mean {number(check['mean_difference'])}, paired SD {number(check['paired_sd_sample'])}, "
              f"95% CI [{number(check['ci95_paired_t'][0])}, {number(check['ci95_paired_t'][1])}], "
              f"exact two-sided paired-t p = `{check['p_two_sided_paired_t']!r}`. "
              "This contradicts the paper's blanket inference from marginal seed SD or from there being only four seeds.", ""]
    for group, info in GROUPS.items():
        rows = [r for r in ROWS if r["group"] == group]
        lines += ["## " + info["title"], "",
                  "| ID | Contrast | Mean difference | Paired SD | 95% paired t CI | Signs −/0/+ (n=4) | Two-sided p | MDD (80%) | Source file :: field (seed 0) |",
                  "|---|---|---:|---:|---|---|---:|---:|---|"]
        for r in rows:
            signs = r["sign_count"]
            lo, hi = r["ci95_paired_t"]
            lines.append(f"| {r['id']} | {r['contrast']} | {number(r['mean_difference'])} | {number(r['paired_sd_sample'])} | "
                         f"[{number(lo)}, {number(hi)}] | {signs['negative']}/{signs['zero']}/{signs['positive']} | "
                         f"{number(r['p_two_sided_paired_t'])} | {number(r['mdd_80pct_alpha05_n4'])} | {source_text(r)} |")
        excludes = [r["id"] for r in rows if r["ci_excludes_zero"]]
        nulls = [f"{r['id']} (MDD {number(r['mdd_80pct_alpha05_n4'])})" for r in rows if r["ci_excludes_zero"] is False]
        identities = [r["id"] for r in rows if r["status"] != "complete"]
        paragraph = ("Paired CIs exclude zero for " + (", ".join(excludes) if excludes else "no contrast") + ". "
                     "The remaining tested contrasts are null at the unadjusted 95% level: " + ("; ".join(nulls) if nulls else "none") + ". ")
        if identities:
            paragraph += "Identity/degenerate reference rows (no test or MDD) are " + ", ".join(identities) + ". "
        paragraph += "These are exploratory paired seed summaries; " + ("the diagnostic is post-hoc and capacity/configuration caveats remain." if any(r["post_hoc"] for r in rows) else "a null CI does not establish equivalence.")
        lines += ["", paragraph, ""]
    lines += ["## Stay-level paired bootstrap of pooled gaps versus GRU-D", "",
              "Each of 2,000 draws samples n evaluable stays with replacement, using the same indices for both fitted models. "
              "For each draw and each model, pooled RMSE = sqrt(sum saved stay SSE / sum saved observed-target count); "
              "the gap is the difference of these two roots. SSE means sum of squared errors. The denominator varies with the resample "
              "and counts repeated stays repeatedly. Zero-target stays contribute no pooled error/count and are excluded from resampling. "
              "Resampling them as eligible zero-contribution records defines a different finite-sample bootstrap; the exclusion here matches "
              "the paper's evaluable-stay convention. The conditional unit is a stay, not a target entry, seed, or person. "
              "The saved SSE arrays use float32 per-stay reductions; totals here use float64, so the array-derived point and frozen run-JSON "
              "point can differ slightly. Both exact points and their difference are retained in JSON. Percentile CIs use NumPy linear quantiles; RNG is default_rng(0) for each seed/split.", "",
              "Coverage is the eight non-GRU-D fitted models with saved per-stay error arrays under results/v4/selected. "
              "Persistence and the two primary learned-graph adapters have no such arrays in that selected series, so no pooled "
              "stay-bootstrap interval is inferred from their scalar RMSE records. Their saved scalar seed contrasts are included above.", "",
              "| ID | Seed | Split | Model − GRU-D | Evaluable stays / eligible | Target entries | Pooled gap | 95% pooled-gap bootstrap CI | Source |",
              "|---|---:|---|---|---:|---:|---:|---|---|"]
    for b in data["pooled_gap_bootstrap"]:
        lo, hi = b["pooled_ci95"]
        lines.append(f"| {b['id']} | {b['seed']} | {b['split']} | {b['model']} | {b['n_resampled_evaluable_stays']}/{b['n_eligible_stays']} | "
                     f"{b['observed_target_entries']} | {number(b['pooled_point_from_saved_arrays'])} | [{number(lo)}, {number(hi)}] | "
                     + " ; ".join(f"`{f} :: sse,count,stay_index,nonfinite`" for f in b["source_files"]) + " |")
    positive = [b["id"] for b in data["pooled_gap_bootstrap"] if b["pooled_ci95"][0] > 0]
    negative = [b["id"] for b in data["pooled_gap_bootstrap"] if b["pooled_ci95"][1] < 0]
    null = [b["id"] for b in data["pooled_gap_bootstrap"] if b["pooled_ci95"][0] <= 0 <= b["pooled_ci95"][1]]
    lines += ["", "Pooled bootstrap CIs exclude zero above zero for " + ", ".join(positive) + "; below zero for " + ", ".join(negative) +
              ". They include zero for " + (", ".join(null) if null else "no contrast") +
              ". These stay-sampling intervals have no n=4 seed MDD; the separate paired seed rows above supply that sensitivity calculation. "
              "Neural CDE B remains an excluded diagnostic, regardless of a numerical interval.", "",
              "## Separate mean-stay RMSE bootstrap versus GRU-D", "",
              "These CIs use the same resampled stays, but average the within-stay square roots before differencing. "
              "Their denominator is the number of evaluable sampled stays, giving each stay equal weight. They are not pooled-gap intervals. "
              "All source paths and excluded counts are the same as the corresponding B_ID in the preceding table; source fields are sse/count followed by the within-stay square root.", "",
              "| Bootstrap ID | Mean-stay gap | 95% mean-stay bootstrap CI |", "|---|---:|---|"]
    for b in data["pooled_gap_bootstrap"]:
        lo, hi = b["mean_stay_ci95"]
        lines.append(f"| {b['id']} | {number(b['mean_stay_point_from_saved_arrays'])} | [{number(lo)}, {number(hi)}] |")
    stay_excludes = [b["id"] for b in data["pooled_gap_bootstrap"] if
                     b["mean_stay_ci95"][0] > 0 or b["mean_stay_ci95"][1] < 0]
    stay_null = [b["id"] for b in data["pooled_gap_bootstrap"] if
                 b["mean_stay_ci95"][0] <= 0 <= b["mean_stay_ci95"][1]]
    lines += ["", "Mean-stay bootstrap CIs exclude zero for " + ", ".join(stay_excludes) +
              ". They include zero for " + (", ".join(stay_null) if stay_null else "no contrast") + ". "
              "These intervals condition on each fitted checkpoint pair and address equal-stay weighting. "
              "They have no n=4 seed MDD; the paired seed tables supply those separately. "
              "For the paper's frozen original float32 PhysioGraph-GRU mean-stay bootstrap, use "
              "`clinical_v4_v1/stats_v4.json :: sampling_uncertainty.seed{0..3}.{A,B}.grud.ci95`; "
              "the present independent float64 calculation may differ in final digits.", "",
              "## Explicit historical Holm families for section 7.1", "",
              "There are eight separate families (four checkpoints × two splits), each with nine members. "
              "Every member compares PhysioGraph-GRU with one of: persistence, GRU, GRU-med, GRU-large, GRU-D, Neural CDE, "
              "ODE-RNN, GraphGRU, PhysioGraph-SSM. Neural CDE B was included in the historical numerical family even though "
              "it is excluded from primary model ranking; it is retained here to reproduce that family rather than silently redefine it. "
              "The tests are two-sided Wilcoxon signed-rank tests on paired stay RMSE differences. "
              "For ordered p(1) ≤ ... ≤ p(9), adjusted p(i) = min(1, max_{j≤i} (10−j)p(j)). "
              "The family contains neither the two learned graphs nor graph variants, horizons, simulator contrasts or the new seed t tests.", "",
              "| Family | n stays | Member (PhysioGraph-GRU − comparator) | Rank | Raw p | Holm p | Source file :: field |",
              "|---|---:|---|---:|---:|---:|---|"]
    for f in data["holm_families"]:
        for m in f["members"]:
            lines.append(f"| {f['id']} | {m['n_evaluable_stays']} | {m['comparator']} | {m['rank']} | {number(m['raw_p'])} | "
                         f"{number(m['adjusted_p_recomputed'])} | `{m['source_file']} :: {m['source_field']}` |")
    lines += ["", "All 72 adjusted p-values reproduce the saved values. For the GRU-D member, all eight Holm-adjusted values "
              "are below 1e-35. These tests have no paired t CI or n=4 MDD, because their sampling unit is a stay; "
              "the separate seed t table answers the four-run question.", "",
              "## Direction accuracy: identifiable counts and missing information", "",
              "The original h5 aggregate has 108 four-seed cells: 96 shared-history and 12 historical legacy cells. "
              "Each run has 120 test patients × 4 adjacent dose pairs × 24 target samples × 6 channels = 69,120 cells. "
              "Removing the first target leaves 66,240 cells. Shared-history exact-zero truth cells number 2,400 (all at the first "
              "target in five channels); CVP has a direct nonzero effect at that target. Legacy rows are historical diagnostics and "
              "do not isolate a shared-versus-legacy protocol effect because sigma differs. Counts below are computed independently "
              "from saved target arrays at the original recorded test indices. Sign numerators and predicted-zero marginals come from "
              "the original per-run direction records and reproduce the h5 aggregate. **Bounds are not point estimates or CIs.**", "",
              "| h5 cell | Protocol | c | sigma | Model | Mean all-cell accuracy | Post-first denominator per seed | Mean post-first accuracy bounds | Exact-zero denominator per seed | Mean exact-zero accuracy | Effect tolerance accuracy | Source aggregate field |",
              "|---|---|---:|---:|---|---:|---:|---|---|---:|---|---|"]
    for d in data["direction_decomposition"]:
        lo, hi = d["mean_post_first_accuracy_bounds"]
        counts = ",".join(str(v["n_true_exact_zero"]) for v in d["per_seed"])
        lines.append(f"| {d['cell_index']} | {d['cf_protocol']} | {number(d['c'])} | {number(d['sigma'])} | {d['model']} | "
                     f"{number(d['mean_all_accuracy'])} | 66240 | [{number(lo)}, {number(hi)}] | {counts} | "
                     f"{number(d['mean_zero_accuracy'])} | BLOCKED | `{d['aggregate_source_file']} :: {d['aggregate_source_field']}` |")
    lines += ["", "These direction rows are descriptive counts and partial-identification bounds, so paired t exclusions and MDD do not "
              "apply to this table. Zero-effect accuracy is exactly zero whenever the saved predicted-zero count is zero; "
              "otherwise the intersection of true-zero and predicted-zero cells is not saved and its rigorous bounds are retained per seed. "
              "An all-cell accuracy does not identify accuracy after the first target is removed: correct first-target CVP cells are unknown. "
              "Similarly, thresholded true-effect counts can be computed from targets but correctness on them requires predictions. "
              "The JSON therefore gives per-seed denominators for exploratory tolerances 1e-6, 1e-4 and 1e-3 times each channel's "
              "range in the saved reference archive (and excludes the first target). Thresholds retain channel units; a cell is eligible "
              "only if its absolute true adjacent-dose effect exceeds that threshold. All corresponding accuracy fields are null. "
              "No threshold was specified in the card; these explicit sensitivity definitions do not claim to be historical choices.", "",
              "## Effect-tolerance denominators from saved target arrays", "",
              "Each entry lists the four per-seed counts in seed order 0,1,2,3. First-target cells are excluded; "
              "only true effects exceeding the channel-specific threshold are eligible. Numerators/accuracies remain unavailable. "
              "For every count and physical threshold, the JSON field is "
              "`direction_decomposition[cell].per_seed[seed].effect_tolerance_variants[tolerance]`; "
              "its truth_source_file/field and range_source_file/field identify the saved arrays exactly.", "",
              "| h5 cell | Protocol | c | sigma | Model | Denominator at 1e-6 × range | At 1e-4 × range | At 1e-3 × range | Accuracy |",
              "|---|---|---:|---:|---|---|---|---|---|"]
    for d in data["direction_decomposition"]:
        counts = [",".join(str(s["effect_tolerance_variants"][j]["denominator_post_nontrivial_effect"])
                           for s in d["per_seed"]) for j in range(3)]
        lines.append(f"| {d['cell_index']} | {d['cf_protocol']} | {number(d['c'])} | {number(d['sigma'])} | "
                     f"{d['model']} | {counts[0]} | {counts[1]} | {counts[2]} | BLOCKED |")
    lines += ["", "This table reports eligible true-effect counts, not a direction-recovery result or a null contrast. "
              "No t CI or MDD applies. Exact accuracy and its paired comparisons remain blocked by missing original predictions. "
              "The saved verifier file `BASE_SIM-verify/artifacts/h5_shared_predictions.npz` was inspected and has only four test patients; "
              "it is a smoke run and cannot replace any full-grid run with 120 test patients.", "",
              "## Delivery limitations and handoff", "",
              "The exact first-target-excluded and effect-tolerance direction scores require the original per-cell predicted trajectories "
              "(or sufficiently detailed sign/effect contingency arrays). Those are absent from the original H5 run tree and aggregate; "
              "its saved NPZs are generated truth/factual datasets. No model was retrained or reinferred. This evidence gap prevents full "
              "acceptance of item 4. The computation is an author/engineer artifact, not an independent scientific review. "
              "The project lead should replace marginal-SD/no-significance language with the paired results, preserving the exploratory status "
              "and multiple-comparison caveats. Current owner final-kit/outside-review workflow applies; the withdrawn automatic editorial "
              "passes and style gates were not reinstated. This is an evidence subtask, not a final paper kit, so prose_metrics is "
              "left to the project lead's once-per-final-kit invocation.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="list historical prerequisites without reading them")
    parser.add_argument("--source-root", type=Path, help="optional complete historical input tree for full recomputation")
    parser.add_argument("--check-original-inputs", action="store_true", help="also check original input hashes; needs the original full tree")
    parser.add_argument("--skip-bootstrap", action="store_true", help="development check only; not a final delivery")
    parser.add_argument("--verify", action="store_true", help="verify existing outputs without rewriting them")
    args = parser.parse_args()
    global PROJECT, MATERIAL
    if args.source_root:
        PROJECT = args.source_root.resolve()
        MATERIAL = PROJECT / 'results'
    if args.dry_run:
        saved = json.loads((HERE / 'paired_stats_v5.json').read_text())
        print(json.dumps({'paired_contrasts': len(saved['paired_contrasts']),
                          'original_inputs': len(saved['inputs']),
                          'available': sum((PROJECT / i['path']).is_file() for i in saved['inputs']),
                          'mode': 'verify saved arithmetic with --verify; full recomputation requires all original inputs and error arrays'}, indent=2))
        return
    if not args.verify and not args.source_root:
        parser.error('use --verify for bundled aggregate arithmetic, or --source-root for a complete historical input tree')
    start = utc()
    clock = time.monotonic()
    if args.verify:
        verify_output(check_original_inputs=args.check_original_inputs)
        return
    E.register(MATERIAL / "sim_grids_v1/overlap_table.csv")
    E.register(MATERIAL / "clinical_v4_v1/tuning_grid.json")
    sim_contrasts()
    clinical_variants()
    primary, primary_get = primary_series()
    shared_contrasts(primary_get)
    horizon_contrasts()
    cinc_contrasts(primary)
    families = holm_families()
    index = h5_runs()
    cf_contrasts(index)
    directions = direction_decomposition(index)
    boot = [] if args.skip_bootstrap else bootstrap_vs_grud()
    data = dict(schema_version="5", task="paired statistics-paired-statistics-build", role="research engineer/author; not independent reviewer",
                status="PARTIAL_DIRECTION_ARRAYS_BLOCKED" if BLOCKERS else "COMPLETE",
                started_utc=start, completed_utc=utc(), elapsed_seconds=time.monotonic() - clock,
                runtime={"python": sys.version, "numpy": np.__version__, "scipy": scipy.__version__, "device": "CPU"},
                methods=dict(n_pairs=4, alpha=.05, confidence=.95, power=.8,
                             mdd="Exact two-sided noncentral t inversion with df=3 and observed paired SD used as planning SD",
                             mdd_multiplier=MDD_FACTOR, mdd_noncentrality=MDD_NCP, mdd_verified_power=MDD_POWER,
                             seed_t_multiple_testing="unadjusted exploratory p-values; historical Holm families are separate",
                             bootstrap_draws=2000, bootstrap_random_seed=0,
                             bootstrap_pooling="sqrt(sum stay SSE / sum observed count), separately per model on each paired resample",
                             direction_status="exact scores partly unidentified without saved per-cell predictions"),
                groups=GROUPS, paired_contrasts=ROWS, holm_families=families,
                pooled_gap_bootstrap=boot, direction_decomposition=directions, blockers=BLOCKERS,
                validation_checks=CHECKS, inputs=sorted(E.inputs.values(), key=lambda z: z["path"]),
                code={"path": "paired_stats.py", "sha256": sha256(__file__)})
    (HERE / "paired_stats_v5.json").write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    (HERE / "PAIRED_STATS_v5.md").write_text(make_markdown(data))
    print(json.dumps(dict(status=data["status"], rows=len(ROWS), groups=len(GROUPS), bootstrap_rows=len(boot),
                          direction_cells=len(directions), holm_families=len(families),
                          checks=len(CHECKS), elapsed_seconds=data["elapsed_seconds"]), indent=2))


def verify_output(check_original_inputs=False):
    x = json.loads((HERE / "paired_stats_v5.json").read_text())
    ids = [r["id"] for r in x["paired_contrasts"]]
    assert len(ids) == len(set(ids))
    assert all(c["pass"] for c in x["validation_checks"])
    for row in x["paired_contrasts"]:
        a = np.array([v["difference"] for v in row["observations"]])
        assert a.shape == (4,)
        if row["status"] == "complete":
            test = stats.ttest_1samp(a, 0.)
            ci = test.confidence_interval(confidence_level=.95)
            assert math.isclose(float(test.pvalue), row["p_two_sided_paired_t"], rel_tol=2e-13, abs_tol=1e-300)
            assert np.allclose([ci.low, ci.high], row["ci95_paired_t"], rtol=2e-14, atol=1e-16)
            critical = stats.t.ppf(.975, 3)
            ncp = row["mdd_80pct_alpha05_n4"] * 2 / row["paired_sd_sample"]
            power = stats.nct.cdf(-critical, 3, ncp) + stats.nct.sf(critical, 3, ncp)
            assert abs(power - .8) < 1e-12
        if row["ci_excludes_zero"] is False:
            assert row["mdd_80pct_alpha05_n4"] is not None
    if check_original_inputs:
        for item in x["inputs"]:
            assert sha256(PROJECT / item["path"]) == item["sha256"], item["path"]
    # Original fingerprints are historical; distributed bytes are checked by SHA256SUMS.

    assert len(x["holm_families"]) == 8 and all(f["family_size"] == 9 for f in x["holm_families"])
    assert len(x["pooled_gap_bootstrap"]) == 64
    assert len(x["direction_decomposition"]) == 108
    pg = [b for b in x["pooled_gap_bootstrap"] if b["model"] == "physiograph_gru"]
    assert len(pg) == 8 and all(b["pooled_ci95"][0] > 0 for b in pg)
    print(json.dumps({"verification": "PASS (available computations only; direction blocker retained)",
                      "paired_rows": len(ids), "historical_inputs_listed": len(x["inputs"]), "original_hashes_checked": check_original_inputs,
                      "bootstrap_rows": len(x["pooled_gap_bootstrap"]), "holms": 72}, indent=2))


if __name__ == "__main__":
    main()
