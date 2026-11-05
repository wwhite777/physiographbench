#!/usr/bin/env python3
"""Print or execute the portable manifest of 88 CinC-2012 runs."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys

from cinc2012_common import (PROJECT, RUN_ROOT, TRANSFER_NPZ, WITHIN_NPZ, SELECTION,
    checkpoint_for, owned_path, verify_input, write_json)

COMMAND_MANIFEST = PROJECT / "manifests/cinc2012_commands.json"


def plan(root=RUN_ROOT, devices=None, threads=None):
    root = owned_path(root)
    verify_input(COMMAND_MANIFEST)
    manifest = json.loads(COMMAND_MANIFEST.read_text())
    devices = list(devices) if devices is not None else manifest["devices"]
    threads = threads if threads is not None else manifest["threads"]
    if not devices or len(set(devices)) != len(devices) or threads < 1:
        raise ValueError("Require distinct explicit devices and positive threads")
    if any(not re.fullmatch(r"cpu|cuda(?::[0-9]+)?", device) for device in devices):
        raise ValueError("Use cpu, cuda or cuda:N devices")
    if "cpu" in devices and len(devices) != 1:
        raise ValueError("CPU execution uses one sequential lane")
    relative_root = str(root.relative_to(PROJECT))
    for index, job in enumerate(manifest["jobs"]):
        command = job["command"]
        command[:] = [part.replace("runs/cinc2012", relative_root) for part in command]
        device = devices[index % len(devices)]
        command[command.index("--device") + 1] = device
        command[command.index("--threads") + 1] = str(threads)
        job["device"] = device
        for key in ("output", "checkpoint_output", "log"):
            if job[key] is not None:
                job[key] = job[key].replace("runs/cinc2012", relative_root)
    manifest.update(root=relative_root, devices=devices, threads=threads)
    for key in ("id", "output", "log"):
        if len({job[key] for job in manifest["jobs"]}) != 88:
            raise ValueError(f"Expected 88 unique {key} values")
    return manifest


def preflight(manifest):
    for path in (TRANSFER_NPZ, WITHIN_NPZ, SELECTION):
        verify_input(path)
    for job in manifest["jobs"]:
        if job["protocol"] == "transfer":
            checkpoint = checkpoint_for(job["model"], job["seed"])
            if not checkpoint.is_file():
                raise FileNotFoundError(f"Missing CinC-2019 checkpoint: {checkpoint}. Run the clinical and learned_graphs suites first.")
            companion = checkpoint.parent / "run.json" if job["model"] not in ("tpatchgnn", "grafiti") else checkpoint.with_suffix(".json")
            if not companion.is_file():
                raise FileNotFoundError(f"Missing source fit record: {companion}")
        dest = owned_path(PROJECT / job["output"]).parent
        log = owned_path(PROJECT / job["log"])
        if (dest.exists() and any(dest.iterdir())) or log.exists():
            raise FileExistsError(f"Preserve prior output/log; inspect before a fresh launch: {job['id']}")
    root = owned_path(PROJECT / manifest["root"])
    for name in ("run_manifest.json", "host_status.json", "cinc2012_results.json", "TABLE_CINC2012.md"):
        if (root / name).exists():
            raise FileExistsError(f"Preserve existing series record: {root / name}")


def execute(manifest):
    preflight(manifest)
    root = owned_path(PROJECT / manifest["root"])
    write_json(root / "run_manifest.json", manifest)

    def lane(device):
        outcomes = []
        for job in manifest["jobs"]:
            if job["device"] != device:
                continue
            log = owned_path(PROJECT / job["log"])
            log.parent.mkdir(parents=True, exist_ok=True)
            print(f"[{device}] {job['id']}", flush=True)
            with log.open("x") as stream:
                code = subprocess.run([sys.executable, *job["command"][1:]], cwd=PROJECT,
                    stdout=stream, stderr=subprocess.STDOUT, check=False).returncode
            output = PROJECT / job["output"]
            record = json.loads(output.read_text()) if output.is_file() else {}
            outcomes.append(dict(id=job["id"], exit_code=code, status=record.get("status", "no_run_record"),
                                 log=job["log"], output=job["output"]))
        return outcomes

    with ThreadPoolExecutor(max_workers=len(manifest["devices"])) as pool:
        lane_results = list(pool.map(lane, manifest["devices"]))
    outcomes = [item for lane_result in lane_results for item in lane_result]
    failed = [record for record in outcomes if record["exit_code"] or record["status"] != "complete"]
    write_json(root / "host_status.json", dict(status="failed_runs" if failed else "runs_complete",
                                               outcomes=outcomes, failed=failed))
    if not failed:
        from aggregate_cinc2012 import aggregate
        aggregate(root)
    return int(bool(failed))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    action = ap.add_mutually_exclusive_group()
    action.add_argument("--run", action="store_true", help="execute all 88 runs after preflight")
    action.add_argument("--dry-run", action="store_true", help="default: print all commands; no data or weights needed")
    device = ap.add_mutually_exclusive_group()
    device.add_argument("--device", help="one explicit device for all jobs, including cpu")
    device.add_argument("--devices", help="comma-separated lanes; default retains the recorded cuda:1,cuda:2,cuda:3")
    ap.add_argument("--out_root", "--out-root", type=Path, default=RUN_ROOT)
    ap.add_argument("--threads", type=int, help="threads per run; default retains the recorded value 4")
    ap.add_argument("--manifest", type=Path, help="write a JSON plan under runs/, also with --dry-run")
    args = ap.parse_args(argv)
    devices = [args.device] if args.device else (args.devices.split(",") if args.devices else None)
    manifest = plan(args.out_root, devices, args.threads)
    if args.manifest:
        destination = owned_path(args.manifest)
        if args.run and destination == PROJECT / manifest["root"] / "run_manifest.json":
            ap.error("--manifest must use a separate plan path; execution writes its own run_manifest.json")
        if destination.exists():
            raise FileExistsError(f"Preserve existing plan: {destination}")
        if args.run:
            preflight(manifest)
        write_json(destination, manifest)
    if args.run:
        return execute(manifest)
    for job in manifest["jobs"]:
        print(f"{shlex.join(job['command'])} > {shlex.quote(job['log'])} 2>&1")
    print(json.dumps(manifest["counts"]), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
