#!/usr/bin/env python3
"""Enumerate the entire host experiment series before launching any GPU work."""
from __future__ import annotations

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH
import argparse
import json
from pathlib import Path
import shlex
import subprocess

from v4_protocol import HERE, PROJECT, MODELS, sha256, write_json
from tuning_grid_runner import grid_jobs
from horizon_table_runner import horizon_jobs
from variant_ablation_runner import variant_jobs

PYTHON = __import__("sys").executable


def plan(root, device="cuda:0", epochs=35, max_stays=None):
    root = Path(root).resolve()
    common = ["--root", str(root), "--device", device, "--epochs", str(epochs)]
    if max_stays is not None:
        common += ["--max-stays", str(max_stays)]
    jobs = []
    def add(identity, script, action, arguments=(), output=None, curve=None, trains=False):
        jobs.append(dict(id=identity, command=[PYTHON, "-u", str(HERE / script), action, *arguments],
                         output=str(output), log=str(root / "logs" / f"{identity}.log"),
                         curve=str(curve) if curve else None, trains=trains))
    for j in grid_jobs():
        ident = f"grid_{j['model']}_{j['cfg']}_seed0"
        add(ident, "tuning_grid_runner.py", "run", [*common, "--model", j["model"], "--lr", str(j["lr"]), "--width", j["width"]],
            root / "grid" / j["model"] / j["cfg"] / "seed0/run.json",
            root / "curves/grid" / f"{j['model']}_{j['cfg']}_seed0.csv", True)
    add("select", "tuning_grid_runner.py", "select", ["--root", str(root)], root / "selection.json")
    for m in MODELS:
        for s in range(4):
            add(f"selected_{m}_seed{s}", "tuning_grid_runner.py", "final", [*common, "--model", m, "--seed", str(s)],
                root / "selected" / m / f"seed{s}/run.json",
                root / "curves/selected" / f"{m}_<selected_cfg>_seed{s}.csv", True)
    add("tuning_summary", "tuning_grid_runner.py", "summarize", ["--root", str(root)], root / "tuning_grid.json")
    for j in variant_jobs():
        if j["reused"]:
            continue
        m, v, s = j["model"], j["variant"], j["seed"]
        add(f"variant_{m}_{v}_seed{s}", "variant_ablation_runner.py", "run", [*common, "--model", m, "--variant", v, "--seed", str(s)],
            root / "variants" / m / v / f"seed{s}/run.json",
            root / "curves/variants" / m / v / f"seed{s}.csv", True)
    add("variant_summary", "variant_ablation_runner.py", "summarize", ["--root", str(root)], root / "variant_ablation_v4.json")
    for j in horizon_jobs():
        m, C, K, s = j["model"], j["C"], j["K"], j["seed"]
        add(f"horizon_C{C}_K{K}_{m}_seed{s}", "horizon_table_runner.py", "run",
            [*common, "--model", m, "--C", str(C), "--K", str(K), "--seed", str(s)],
            root / "horizons" / f"C{C}_K{K}" / m / f"seed{s}/run.json",
            root / "curves/horizons" / f"C{C}_K{K}" / f"{m}_seed{s}.csv", True)
    add("horizon_summary", "horizon_table_runner.py", "summarize", ["--root", str(root)], root / "horizon_table_v4.json")
    # These commands have no positional action argument; construct directly.
    for ident, script, output in (("selected_stats", "patient_level_stats.py", "stats_v4.json"),
                                  ("selected_organs", "per_organ_table.py", "per_organ_v4.json")):
        jobs.append(dict(id=ident, command=[PYTHON, "-u", str(HERE / script), "--series-root", str(root), "--out", str(root / output)],
                         output=str(root / output), log=str(root / "logs" / f"{ident}.log"), curve=None, trains=False))
    jobs.append(dict(id="ncde_diagnosis", command=[PYTHON, "-u", str(HERE / "ncde_diagnosis.py"),
        "--checkpoint", str(root / "selected/ncde/seed0/checkpoint.pt"), "--out", str(root / "ncde_diagnosis.md"), "--trace", str(root / "ncde_trace.json")],
        output=str(root / "ncde_diagnosis.md"), log=str(root / "logs/ncde_diagnosis.log"), curve=None, trains=False))
    for key in ("id", "output", "log"):
        vals = [j[key] for j in jobs]
        if len(vals) != len(set(vals)):
            raise ValueError(f"duplicate host {key}")
    curves = [j["curve"] for j in jobs if j["curve"]]
    if len(curves) != len(set(curves)):
        raise ValueError("duplicate convergence curves")
    return dict(schema_version=4, root=str(root), device=device, epochs_budget=epochs,
        grid_seed=0, seeds=[0, 1, 2, 3], max_stays=max_stays,
        counts=dict(grid=54, selected=36, extra_variants=40, horizons=180, total_fits=310,
                    reused_admissible_variants=8, commands=len(jobs)), jobs=jobs,
        note="<selected_cfg> resolves from validation-only selection.json; all other output/log paths are fixed before execution.")


def check_gate(waiver_reason=None):
    """Verify portable inputs; the historical interval exception is in frozen results."""
    file = PROJECT / "manifests/distribution.json"
    entries = json.loads(file.read_text())
    for name, item in entries.items():
        if name.endswith(".py") and sha256(PROJECT / name) != item["distributed_sha256"]:
            raise RuntimeError(f"distributed source changed: {name}")
    cohort = PROJECT / "data/cinc2019_cohort.npz"
    expected = "d52d8131323fc7a3838ae4fe523c2edbc02d2daa781de1859e7d184897dfb51f"
    if sha256(cohort) != expected:
        raise RuntimeError("cohort differs from the frozen protocol")
    return dict(status="PASS", scope="distribution and cohort integrity",
                historical_interval_exception="retained in results/v4/run_manifest_with_waiver.json")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=PROJECT / "runs/clinical")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--manifest", type=Path, help="optional explicit plan file, including for a dry run")
    args = ap.parse_args(argv)
    manifest = plan(args.root, args.device)
    if args.manifest:
        write_json(args.manifest, manifest)
    if args.dry_run:
        for job in manifest["jobs"]:
            print(f"{shlex.join(job['command'])} > {shlex.quote(job['log'])} 2>&1")
        print(json.dumps(manifest["counts"]))
        return 0
    # The worker never executes this branch; the maintainer owns result/v4 and the GPU.
    if args.root.resolve() != (PROJECT / "runs/clinical").resolve():
        ap.error("full host execution is confined to the authorized result/v4 directory")
    gate = check_gate()
    if args.root.exists():
        ap.error("result/v4 already exists; preserve existing results and reconcile with maintainer")
    args.root.mkdir(parents=True)
    write_json(args.root / "run_manifest.json", dict(manifest, headline_gate=gate))
    failures = []
    for job in manifest["jobs"]:
        log = Path(job["log"])
        log.parent.mkdir(parents=True, exist_ok=True)
        print(f"[host] {job['id']}", flush=True)
        with log.open("x") as f:
            code = subprocess.run(job["command"], stdout=f, stderr=subprocess.STDOUT, check=False).returncode
        if code:
            failures.append(dict(id=job["id"], exit_code=code, log=str(log)))
            if job["id"] == "select":
                break
    write_json(args.root / "host_status.json", dict(failures=failures,
        status="failed_commands" if failures else "commands_finished; inspect every run status before scientific claims",
        headline_gate=gate))
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
