#!/usr/bin/env python3
"""Enumerate 8 fits + 8 evaluations on configurable GPU lanes."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

from n3_common import (HERE, PROJECT, TASK, SCRATCH, FULL_ROOT, PYTHON, CAPS,
                       identities, checkpoint_for, run_dir, fresh_path, owned_path,
                       verify_input, sha256, write_json)


def plan(root=FULL_ROOT, devices=("2", "3"), threads=2):
    root = owned_path(root)
    if not devices or len(set(devices)) != len(devices) or any(not d.isdecimal() for d in devices):
        raise ValueError("Require distinct nonnegative GPU lane IDs")
    if threads < 1:
        raise ValueError("threads must be positive")
    jobs = []
    for protocol, arm, seed in identities():
        gpu = devices[len(jobs) % len(devices)]
        ident = f"{protocol}_shared_{arm}_epochs{CAPS[arm]}_seed{seed}"
        command = [PYTHON, "-B", "-u", str(HERE / "run_n3.py"), "--protocol", protocol,
            "--arm", arm, "--seed", str(seed), "--out-root", str(root), "--device", "cuda:0",
            "--epochs", str(CAPS[arm]), "--batch", "128", "--threads", str(threads)]
        env = dict(CUDA_VISIBLE_DEVICES=gpu, CUBLAS_WORKSPACE_CONFIG=":4096:8",
                   TMPDIR=str(SCRATCH), TMP=str(SCRATCH), TEMP=str(SCRATCH), PYTHONDONTWRITEBYTECODE="1")
        jobs.append(dict(id=ident, protocol=protocol, arm=arm, seed=seed, selected_epochs_cap=CAPS[arm],
            gpu=gpu, command=command, environment=env,
            output=str(run_dir(root, protocol, arm, seed) / "run.json"),
            log=str(root / "logs" / f"{ident}.log"),
            source_checkpoint=str(checkpoint_for(arm, seed)) if protocol == "transfer" else None,
            expected_gpu_seconds=[600, 1800] if protocol == "within" else [10, 45]))
    for key in ("id", "output", "log"):
        if len({j[key] for j in jobs}) != 16:
            raise ValueError(f"Expected 16 unique {key} values")
    return dict(schema_version=1, task=TASK, root=str(root), devices=list(devices), jobs=jobs,
        counts=dict(within_fits=8, transfer_evaluations=8, total=16), threads=threads,
        selected_caps=CAPS, distribution_inventory_sha256=sha256(PROJECT / "manifests/distribution.json"),
        local_source_sha256={p.name: sha256(p) for p in sorted(HERE.glob("*.py"))},
        output_budget=dict(expected_bytes=128 * 1024**2, sampled_growth_limit_bytes=2 * 1024**3,
            temporary_overlap_bytes=32 * 1024**2, input_copy_bytes=0,
            recovery="Preserve partial runs/logs. Diagnose, then use a fresh approved output root; never overwrite."),
        execution_note="Two sequential process lanes; CUDA_VISIBLE_DEVICES selects each physical GPU and each job uses cuda:0. No job/session termination.",
        timing_note="Planning estimates, not new GPU measurements; fits 10-30 min/job, transfer 10-45 s/job. Early stopping can shorten fits.")


def preflight(manifest):
    fresh_path(manifest["root"])
    for source in ('tools/v4_protocol.py', 'tools/cinc2012/cinc2012_common.py', 'experiments/shared_input_primary/shared_input_primary.py'):
        verify_input(PROJECT / source)
    for job in manifest["jobs"]:
        fresh_path(Path(job["output"]).parent)
        fresh_path(job["log"])
    # Import/validate all eight source checkpoints before reserving any outputs.
    from run_n3 import load_checkpoint
    for arm in CAPS:
        for seed in range(4):
            load_checkpoint(arm, seed, "cpu")
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("maintainer GPU host required; worker may only dry-run and CPU smoke")
    visible = os.environ.get("CUDA_VISIBLE_DEVICES")
    if visible and visible != ",".join(manifest["devices"]):
        raise RuntimeError("Unset GPU visibility or match it to the selected physical lane IDs")
    if not visible and torch.cuda.device_count() <= max(int(d) for d in manifest["devices"]):
        raise RuntimeError("Requested physical GPU lane is unavailable")


def execute(manifest):
    preflight(manifest)
    root = fresh_path(manifest["root"])
    root.mkdir(parents=True, exist_ok=False)
    write_json(root / "run_manifest.json", manifest)

    def lane(gpu):
        outcomes = []
        for job in manifest["jobs"]:
            if job["gpu"] != gpu:
                continue
            log = fresh_path(job["log"])
            log.parent.mkdir(parents=True, exist_ok=True)
            started = datetime.now(timezone.utc).isoformat()
            env = os.environ.copy()
            env.update(job["environment"])
            print(f"[GPU {gpu}] {job['id']}", flush=True)
            with log.open("x") as stream:
                code = subprocess.run(job["command"], env=env, cwd=PROJECT,
                    stdout=stream, stderr=subprocess.STDOUT, check=False).returncode
            path = Path(job["output"])
            record = json.loads(path.read_text()) if path.is_file() else {}
            outcome = dict(id=job["id"], started_utc=started,
                ended_utc=datetime.now(timezone.utc).isoformat(), exit_code=code,
                status=record.get("status", "no_run_record"), output=job["output"], log=str(log))
            outcomes.append(outcome)
            write_json(root / "job_status" / f"{job['id']}.json", outcome)
            if code or outcome["status"] != "complete":
                # Preserve this lane's unstarted work; never retry automatically.
                break
        return outcomes

    with ThreadPoolExecutor(max_workers=len(manifest["devices"])) as pool:
        lane_results = list(pool.map(lane, manifest["devices"]))
    outcomes = [r for lane_outcomes in lane_results for r in lane_outcomes]
    complete = len(outcomes) == 16 and all(r["exit_code"] == 0 and r["status"] == "complete" for r in outcomes)
    write_json(root / "host_status.json", dict(status="runs_complete" if complete else "incomplete",
        outcomes=outcomes, expected_jobs=16, completed_jobs=sum(r["status"] == "complete" for r in outcomes)))
    return 0 if complete else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--dry-run", action="store_true", help="default")
    ap.add_argument("--devices", default="2,3", help="comma-separated physical GPU IDs")
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--out-root", type=Path, default=FULL_ROOT)
    ap.add_argument("--manifest", type=Path, help="exclusive optional plan output")
    args = ap.parse_args(argv)
    manifest = plan(args.out_root, tuple(args.devices.split(",")), args.threads)
    if args.manifest:
        write_json(args.manifest, manifest)
    if args.run:
        return execute(manifest)
    for job in manifest["jobs"]:
        assignments = [f"{key}={value}" for key, value in job["environment"].items()]
        print(f"env {shlex.join(assignments + job['command'])} > {shlex.quote(job['log'])} 2>&1")
    print(json.dumps(manifest["counts"]), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
