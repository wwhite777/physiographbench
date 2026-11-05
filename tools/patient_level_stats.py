#!/usr/bin/env python3
"""Paired stay bootstrap within a checkpoint; seed variation is reported separately."""
from __future__ import annotations

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH
import argparse
import json
from pathlib import Path

from v4_protocol import (ALL_MODELS, HERE, PROJECT, SIZES_FROZEN, add_data_args, build,
                         collect_errors, make_data, metrics, save_errors, sha256,
                         write_json, finite_float, runtime)
import numpy as np
import torch
from scipy import stats


def paired_stats(reference, comparator, n_boot=2000, rng_seed=0, include_zero_targets=False):
    if not np.array_equal(reference["stay_index"], comparator["stay_index"]):
        raise ValueError("paired stays differ or are in a different order")
    if not np.array_equal(reference["count"], comparator["count"]):
        raise ValueError("paired observation masks differ")
    valid = ((reference["count"] >= 0) if include_zero_targets else (reference["count"] > 0)) & np.isfinite(reference["sse"]) & np.isfinite(comparator["sse"])
    if not valid.all():
        # Do not silently discard a model's nonfinite predictions.
        if np.any(~np.isfinite(reference["sse"])) or np.any(~np.isfinite(comparator["sse"])):
            return dict(status="nonfinite_model_errors", n_stays=len(valid),
                        excluded_nonfinite=int((~np.isfinite(reference["sse"]) | ~np.isfinite(comparator["sse"])).sum()))
    denominator = np.maximum(reference["count"][valid], 1)
    ra = reference["sse"][valid] / denominator
    rb = comparator["sse"][valid] / denominator
    diff = np.sqrt(ra) - np.sqrt(rb)
    n = len(diff)
    if not n:
        return dict(status="no_observed_targets", n_stays=len(valid))
    if n_boot < 100:
        raise ValueError("at least 100 bootstrap draws required")
    rng = np.random.default_rng(rng_seed)
    # Keep float32 arithmetic here to reproduce the frozen earlier benchmark bootstrap exactly.
    boot = np.array([diff[rng.integers(0, n, n)].mean() for _ in range(n_boot)])
    def wilcoxon(delta):
        if np.all(delta == 0):
            return dict(statistic=0.0, p_value=1.0)
        w = stats.wilcoxon(delta, alternative="two-sided", zero_method="wilcox", method="auto")
        return dict(statistic=float(w.statistic), p_value=float(w.pvalue))
    return dict(status="complete", n_stays=n, n_eligible_stays=len(valid),
                zero_target_stays_excluded=int((~valid).sum()),
                historical_zero_target_clamping=include_zero_targets,
                estimand="mean across stays of (PhysioGraph-GRU window RMSE minus comparator window RMSE)",
                mean_window_RMSE_gap=float(diff.mean()), ci95=np.percentile(boot, [2.5, 97.5]).tolist(),
                reference_mean_window_RMSE=float(np.sqrt(ra).mean()),
                comparator_mean_window_RMSE=float(np.sqrt(rb).mean()),
                reference_sqrt_mean_window_MSE=float(np.sqrt(ra.mean())),
                comparator_sqrt_mean_window_MSE=float(np.sqrt(rb.mean())),
                comparator_better_fraction=float((diff > 0).mean()),
                wilcoxon_window_RMSE=wilcoxon(diff),
                historical_wilcoxon_window_MSE=wilcoxon(ra - rb),
                bootstrap=dict(draws=n_boot, seed=rng_seed, unit="stay", paired=True,
                               interval="percentile", confidence=0.95))


def holm_adjust(comparisons):
    good = [(k, v["wilcoxon_window_RMSE"]["p_value"]) for k, v in comparisons.items()
            if v.get("status") == "complete"]
    floor = 0.0
    for rank, (key, p) in enumerate(sorted(good, key=lambda pair: pair[1])):
        floor = max(floor, min(1.0, p * (len(good) - rank)))
        comparisons[key]["wilcoxon_window_RMSE"]["p_holm_within_checkpoint_split"] = floor


def seed_summary(seed_files):
    runs = []
    for path in sorted(seed_files):
        raw = json.loads(Path(path).read_text())
        runs.append((raw["config"]["seed"], raw["results"], str(path), sha256(path)))
    if len({r[0] for r in runs}) != len(runs):
        raise ValueError("duplicate seed in aggregate files")
    out = dict(estimand="pooled observed-entry RMSE reported by each seed JSON; not mean window RMSE",
               source_files=[dict(path=r[2], sha256=r[3], seed=r[0]) for r in runs], models={}, comparisons={})
    for name in ALL_MODELS:
        out["models"][name] = {}
        for split, key in (("A", "A_test"), ("B", "B_external")):
            vals = [(s, r[name][key]["RMSE@12"]) for s, r, _, _ in runs if name in r]
            out["models"][name][split] = dict(n_seeds=len(vals), per_seed=dict(vals),
                mean=float(np.mean([v for _, v in vals])) if vals else None,
                sd_population=float(np.std([v for _, v in vals], ddof=0)) if vals else None,
                sd_sample=float(np.std([v for _, v in vals], ddof=1)) if len(vals) > 1 else None)
            if name == "physiograph_gru":
                continue
            pairs = [(s, r["physiograph_gru"][key]["RMSE@12"] - r[name][key]["RMSE@12"])
                     for s, r, _, _ in runs if name in r and "physiograph_gru" in r]
            v = np.array([x for _, x in pairs])
            out["comparisons"].setdefault(name, {})[split] = dict(
                n_seeds=len(v), per_seed_gap=dict(pairs), mean_gap=float(v.mean()) if len(v) else None,
                sd_sample=float(v.std(ddof=1)) if len(v) > 1 else None,
                t95_ci=(v.mean() + np.array([-1, 1]) * stats.t.ppf(.975, len(v) - 1)
                        * v.std(ddof=1) / np.sqrt(len(v))).tolist() if len(v) > 1 else None,
                paired_t_p=finite_float(stats.ttest_1samp(v, 0).pvalue) if len(v) > 1 and np.any(v) else None)
    return out


def evaluate_frozen(args):
    loaders, meta = make_data(args.npz, batch=args.batch, max_stays=args.max_stays)
    if args.reuse_errors:
        old = json.loads(args.reuse_errors.read_text())
        if old["data"] != meta:
            raise ValueError("cached errors have a different cohort/protocol")
        for name, expected in old.get("source_sha256", {}).items():
            if sha256(PROJECT / "src" / name) != expected:
                raise ValueError(f"frozen source changed since cached inference: {name}")
        grouped = {}
        for label, models in old["checkpoints"].items():
            for name, item in models.items():
                if item.get("checkpoint") and sha256(item["checkpoint"]) != item["checkpoint_sha256"]:
                    raise ValueError("cached checkpoint changed")
                for split, entry in item["splits"].items():
                    if sha256(entry["error_file"]) != entry["sha256"]:
                        raise ValueError("cached error artifact changed")
                    with np.load(entry["error_file"]) as archive:
                        grouped.setdefault(label, {}).setdefault(split, {})[name] = dict(archive)
        return grouped, old["checkpoints"], meta
    records = []
    if args.checkpoint_manifest:
        records = json.loads(args.checkpoint_manifest.read_text())["checkpoints"]
        if len({(r["label"], r["model"]) for r in records}) != len(records):
            raise ValueError("duplicate checkpoint/model label")
    else:
        records = [dict(label="frozen_unattributed", seed=None, model=m,
                        path=str(PROJECT / f"ckpt/{m}.pt"), sizes=SIZES_FROZEN,
                        variant="admissible") for m in ALL_MODELS]
    grouped, artifacts = {}, {}
    for r in records:
        name, label = r["model"], r["label"]
        model = None
        if name != "persistence":
            model = build(name, r.get("sizes", SIZES_FROZEN), r.get("variant", "admissible"))
            state = torch.load(r["path"], map_location="cpu", weights_only=True)
            model.load_state_dict(state.get("state_dict", state))
        item = dict(seed=r.get("seed"), checkpoint=r.get("path") if model is not None else None,
                    checkpoint_sha256=sha256(r["path"]) if model is not None else None, splits={})
        for split, loader in zip(("A", "B"), loaders[2:]):
            e = collect_errors(model, loader, device="cpu", organ_slices=meta["organ_slices"])
            path = args.artifact_dir / label / f"{name}_{split}.npz"
            save_errors(path, e)
            grouped.setdefault(label, {}).setdefault(split, {})[name] = e
            item["splits"][split] = dict(error_file=str(path.resolve()), sha256=sha256(path),
                                        metrics=metrics(e, meta["organ_names"]))
        artifacts.setdefault(label, {})[name] = item
        print(f"evaluated {label}/{name} on CPU", flush=True)
    return grouped, artifacts, meta


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    add_data_args(ap)
    ap.add_argument("--out", type=Path, default=HERE / "stats_v4.json")
    ap.add_argument("--artifact-dir", type=Path, default=HERE / "artifacts/frozen_errors")
    ap.add_argument("--checkpoint-manifest", type=Path, help='JSON {"checkpoints":[{label,seed,model,path,sizes,variant}]}')
    ap.add_argument("--series-root", type=Path, help="use errors from selected/<model>/seed<k> runs instead of frozen checkpoints")
    ap.add_argument("--reuse-errors", type=Path, help="reuse SHA-verified inference artifacts indexed in an earlier stats JSON")
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--require-headline", action="store_true", help="nonzero exit if the frozen CI acceptance fails")
    args = ap.parse_args(argv)
    torch.set_num_threads(args.threads)
    if args.series_root:
        grouped, artifacts, meta = {}, {}, None
        for file in sorted((args.series_root / "selected").glob("*/seed*/run.json")):
            r = json.loads(file.read_text())
            label, name = f"seed{r['seed']}", r["model"]
            artifacts.setdefault(label, {})[name] = dict(seed=r["seed"], status=r["status"], run=str(file), sha256=sha256(file))
            if r["status"] != "complete":
                continue
            if meta is not None and r["data"]["split_stay_indices"] != meta["split_stay_indices"]:
                raise ValueError("series split mismatch")
            meta = r["data"]
            for split in ("A", "B"):
                with np.load(file.parent / f"errors_{split}.npz") as f:
                    grouped.setdefault(label, {}).setdefault(split, {})[name] = dict(f)
        if meta is None:
            raise ValueError("no completed selected runs")
        loaders, baseline_meta = make_data(args.npz, C=meta["C"], K=meta["K"], batch=args.batch,
                                           max_stays=meta["max_stays"], min_length=meta["min_length"])
        if baseline_meta["split_stay_indices"] != meta["split_stay_indices"]:
            raise ValueError("persistence baseline stays differ")
        for split, loader in zip(("A", "B"), loaders[2:]):
            errors = collect_errors(None, loader, K=meta["K"], organ_slices=meta["organ_slices"])
            for label in artifacts:
                grouped.setdefault(label, {}).setdefault(split, {})["persistence"] = errors
    else:
        grouped, artifacts, meta = evaluate_frozen(args)
    comparisons = {}
    for label, splits in grouped.items():
        for split, models in splits.items():
            c = {name: (paired_stats(models["physiograph_gru"], models[name], args.n_boot)
                        if name in models and "physiograph_gru" in models else dict(status="failed_or_missing_checkpoint"))
                 for name in ALL_MODELS if name != "physiograph_gru"}
            holm_adjust(c)
            comparisons.setdefault(label, {})[split] = c
    gate = dict(status="not_applicable", target_ci95=[.022, .028], tolerance=.001)
    if "frozen_unattributed" in comparisons and args.max_stays is None:
        errors = grouped["frozen_unattributed"]["A"]
        headline = paired_stats(errors["physiograph_gru"], errors["grud"], args.n_boot, include_zero_targets=True)
        ci = headline.get("ci95")
        passed = (ci is not None and args.n_boot == 2000
                  and np.all(np.abs(np.array(ci) - [.022, .028]) <= .001) and headline["n_stays"] == 2368)
        gate.update(status="PASS" if passed else "FAIL", actual_ci95=ci,
                    reproduction_statistic=headline,
                    frozen_published_ci95=[.02200615592300892, .028484975919127464])
    summary = seed_summary((PROJECT / "result/seeds").glob("forecast_seed[0-3].json"))
    out = dict(schema_version=4, scope="smoke" if meta["max_stays"] is not None else "full",
               claim_status="BLOCKED_HEADLINE_REPRODUCTION" if gate["status"] == "FAIL" else "no new ordering claim; full runs and scientific verification required",
               role="research engineer/author; independent verification pending",
               data=meta, runtime=runtime(), direction="positive gap means comparator has lower error than PhysioGraph-GRU",
               sampling_uncertainty=comparisons, checkpoints=artifacts,
               legacy_seed_uncertainty=summary, headline_reproduction=gate,
               source_sha256={p.name: sha256(p) for p in sorted((PROJECT / "src").glob("*.py"))},
               limits=["Singleton frozen checkpoints have no saved seed provenance; never relabel as seeds 0–3.",
                       "Seed-specific frozen sampling intervals cannot be recovered from aggregate JSONs.",
                       "Mean stay RMSE, sqrt(mean stay MSE), and pooled observed-entry RMSE are distinct estimands.",
                       "Nonfinite predictions invalidate a comparison; missing target entries are not zero-error observations."])
    if args.series_root:
        out["selected_seed_uncertainty"] = {}
        for split in ("A", "B"):
            names = [m for m in ALL_MODELS if m != "physiograph_gru"]
            out["selected_seed_uncertainty"][split] = {}
            for name in names:
                per_seed = {f"seed{i}": comparisons.get(f"seed{i}", {}).get(split, {}).get(name, {}).get("mean_window_RMSE_gap")
                            for i in range(4)}
                values = [v for v in per_seed.values() if v is not None]
                out["selected_seed_uncertainty"][split][name] = dict(
                    expected_seeds=4, n_completed_seeds=len(values),
                    status="complete" if len(values) == 4 else "incomplete",
                    per_seed_mean_window_gap=per_seed,
                    mean_gap=float(np.mean(values)) if values else None,
                    sd_sample=float(np.std(values, ddof=1)) if len(values) > 1 else None)
        out["selected_model_seed_uncertainty"] = {}
        for name in ALL_MODELS:
            for split in ("A", "B"):
                per_seed = {}
                for label, splits in grouped.items():
                    e = splits.get(split, {}).get(name)
                    if e is not None and np.isfinite(e["sse"]).all():
                        valid = e["count"] > 0
                        per_seed[label] = float(np.sqrt(e["sse"][valid] / e["count"][valid]).mean()) if valid.any() else None
                values = [v for v in per_seed.values() if v is not None]
                out["selected_model_seed_uncertainty"].setdefault(name, {})[split] = dict(
                    estimand="per-seed mean stay RMSE, excluding stays without observed targets",
                    per_seed=per_seed, expected_seeds=4, n_completed_seeds=len(values),
                    status="complete" if len(values) == 4 else "incomplete",
                    mean=float(np.mean(values)) if values else None,
                    sd_sample=float(np.std(values, ddof=1)) if len(values) > 1 else None)
    write_json(args.out, out)
    print(json.dumps(gate), flush=True)
    if args.require_headline and gate["status"] != "PASS":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
