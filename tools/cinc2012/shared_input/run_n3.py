#!/usr/bin/env python3
"""One N3 shared-input within fit or frozen-checkpoint transfer evaluation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

from n3_common import (PROJECT, HERE, FULL_ROOT, TASK, MODEL, CAPS, WITHIN_NPZ, TRANSFER_NPZ,
                       SELECTION, checkpoint_for, selected_config, verify_input,
                       sha256, fresh_path, run_dir, write_json)


def load_checkpoint(arm, seed, device):
    from n3_runtime import shared
    import torch
    choice = selected_config()
    path = checkpoint_for(arm, seed)
    if not path.is_file(): raise FileNotFoundError(f"Reproduce the selected 2019 checkpoint first: {path}")
    record_path = path.parent / "run.json"
    r = json.loads(record_path.read_text())
    for key, expected in dict(model=MODEL, arm=arm, seed=seed, status="complete", scope="full",
                              epochs_budget=CAPS[arm], sizes=choice["sizes"], lr=choice["lr"],
                              width=choice["width"], C=12, K=12, batch=128).items():
        if r[key] != expected:
            raise ValueError(f"Wrong 2019 source record {key}: {record_path}")
    if r["checkpoint_sha256"] != sha256(path) or r["data"]["cohort_sha256"] != shared.COHORT_SHA256:
        raise ValueError("2019 checkpoint hash/cohort mismatch")
    payload = torch.load(path, map_location="cpu", weights_only=True)
    net = shared.build_arm(arm, choice["sizes"])
    for key, expected in dict(model=MODEL, arm=arm, seed=seed, sizes=choice["sizes"],
                              lr=choice["lr"], width=choice["width"], C=12, K=12,
                              edges=[list(e) for e in shared.edges_for(arm)],
                              cohort_sha256=shared.COHORT_SHA256).items():
        if payload[key] != expected:
            raise ValueError(f"Wrong 2019 checkpoint payload {key}: {path}")
    net.load_state_dict(payload["state_dict"], strict=True)
    return net.to(device), dict(path=str(path), sha256=sha256(path), source_record=str(record_path),
        source_record_sha256=sha256(record_path), epochs_budget=CAPS[arm],
        best_epoch=r["best_epoch"], config={k: choice[k] for k in ("lr", "width", "sizes")})


def run(protocol, arm, seed, *, out_root=FULL_ROOT, device="cpu", epochs=None,
        max_stays=None, batch=128, threads=2):
    if protocol not in ("within", "transfer") or arm not in CAPS or seed not in range(4):
        raise ValueError("Unregistered N3 identity")
    if batch != 128 or threads < 1:
        raise ValueError("Batch=128; threads must be positive")
    cap = CAPS[arm]
    epochs = cap if epochs is None else epochs
    if max_stays is None:
        if epochs != cap:
            raise ValueError("Full runs require the validation-selected epoch cap")
        if str(device).split(":")[0] != "cuda":
            raise ValueError("CPU is limited to smoke tests; full runs require maintainer CUDA")
    elif not (8 <= max_stays <= 64 and 1 <= epochs <= cap):
        raise ValueError("Smoke requires 8..64 total stays and 1..selected-cap epochs")
    if protocol == "transfer" and epochs != cap:
        raise ValueError("Transfer checkpoint cap is fixed, even for smoke inference")
    dest = fresh_path(run_dir(out_root, protocol, arm, seed))
    from n3_runtime import clinical_base, training, v4, shared
    import numpy as np
    import torch
    started = time.monotonic()
    device = clinical_base.setup_device(device, threads)
    choice = selected_config()
    npz = verify_input(WITHIN_NPZ if protocol == "within" else TRANSFER_NPZ)
    # Exclusive reservation before any internal writer runs. A partial directory
    # blocks another invocation, even if training failed before run.json existed.
    dest.mkdir(parents=True, exist_ok=False)
    if protocol == "within":
        result = training.train_run(MODEL, choice["lr"], choice["width"], seed, dest,
            npz=npz, epochs=epochs, batch=batch, device=device, max_stays=max_stays,
            variant=arm, evaluate_tests=False)
        # The frozen loop writes its own intermediate record; complete the same
        # owned record only within this reserved invocation.
        if result["status"] != "complete":
            raise RuntimeError(f"Within fit failed: {result.get('failure')}")
        net = shared.build_arm(arm, choice["sizes"]).to(device)
        payload = torch.load(dest / "checkpoint.pt", map_location="cpu", weights_only=True)
        net.load_state_dict(payload["state_dict"], strict=True)
        loaders, _ = clinical_base.make_data(npz, "within", batch, seed, max_stays)
        meta = result["data"]
        _, metric = clinical_base.evaluate_split(net, loaders["testB"], meta, device, dest, "testB")
        results = dict(testB=metric)
        result.update(scheduler_T_max=epochs,
            evaluation_note="test_idx/testA is empty by design; evaluate set-b (testB) only")
    else:
        v4.seed_all(seed)
        net, checkpoint = load_checkpoint(arm, seed, device)
        loaders, meta = clinical_base.make_data(npz, "transfer", batch, seed, max_stays)
        results, errors = {}, []
        for split, loader in loaders.items():
            err, results[split] = clinical_base.evaluate_split(net, loader, meta, device, dest, split)
            errors.append(err)
        pooled = {key: np.concatenate([e[key] for e in errors]) for key in errors[0]}
        results["pooled"] = v4.metrics(pooled, meta["organ_names"])
        result = dict(checkpoint=checkpoint, data=meta, epochs_budget=cap, status="complete")
    result.update(schema_version=1, task=TASK, decision_id="D-016 addendum 2", protocol=protocol,
        model=MODEL, arm=arm, variant=arm, seed=seed, C=12, K=12, batch=batch, device=device,
        scope="smoke" if max_stays is not None else "full", selected_epochs_cap=cap,
        input_mode="shared", training_performed=protocol == "within", results=results,
        lr=choice["lr"], width=choice["width"], sizes=choice["sizes"],
        n_params=sum(p.numel() for p in net.parameters()), edges=[list(e) for e in shared.edges_for(arm)],
        node_input_widths=list(net.node_input_widths),
        projection_input_widths=[p.in_features for p in net.in_proj],
        selection_file=str(SELECTION), selection_sha256=sha256(SELECTION),
        threads=threads, cublas_workspace_config=":4096:8",
        deterministic_algorithms=torch.are_deterministic_algorithms_enabled(),
        distribution_inventory_sha256=sha256(PROJECT / "manifests/distribution.json"),
        local_source_sha256={p.name: sha256(p) for p in sorted(HERE.glob("*.py"))},
        source_sha256=clinical_base.runtime_sources(), runtime=v4.runtime(), seconds=time.monotonic() - started)
    if protocol == "within":
        (dest / "run.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    else:
        write_json(dest / "run.json", result)
    print(json.dumps(dict(protocol=protocol, arm=arm, seed=seed, scope=result["scope"],
        results={s: m["pooled_masked_RMSE"] for s, m in results.items()})), flush=True)
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--protocol", choices=("within", "transfer"), required=True)
    ap.add_argument("--arm", choices=CAPS, required=True)
    ap.add_argument("--seed", type=int, choices=range(4), required=True)
    ap.add_argument("--out-root", type=Path, default=FULL_ROOT)
    ap.add_argument("--device", required=True)
    ap.add_argument("--epochs", type=int)
    ap.add_argument("--max-stays", type=int)
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--threads", type=int, default=2)
    run(**vars(ap.parse_args(argv)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
