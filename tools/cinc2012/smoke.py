#!/usr/bin/env python3
"""One CPU within-corpus fit and, when available, a 2019-checkpoint transfer check."""
from pathlib import Path
import tempfile

from cinc2012_common import PROJECT, MODELS, checkpoint_for, write_json
from cinc2012_within_runner import run as within


def main():
    parent = PROJECT / "runs/cinc2012-smoke"
    parent.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="run-", dir=parent))
    result = within("gru", 0, out_root=root, device="cpu", threads=1, max_stays=64, epochs=1)
    if result["status"] != "complete" or result["epochs_completed"] != 1:
        raise RuntimeError("Within-corpus smoke did not complete its single epoch")
    # Use a completed 2019 source fit, never the within-2012 checkpoint just created.
    available = [(model, seed) for model in MODELS for seed in range(4)
                 if checkpoint_for(model, seed).is_file()]
    if available:
        from cinc2012_transfer_eval import run as transfer
        model, seed = available[0]
        transfer(model, seed, out_root=root, device="cpu", threads=1, max_stays=64)
        transfer_status = f"PASS: {model}, seed {seed}"
    else:
        transfer_status = "SKIP: no CinC-2019 source checkpoint in the distribution; retrain the clinical and learned_graphs suites first"
        print(transfer_status, flush=True)
    write_json(root / "smoke_status.json", dict(within="PASS", transfer=transfer_status,
        max_stays=64, epochs=1, device="cpu"))
    print(f"CinC-2012 smoke PASS; outputs: {root.relative_to(PROJECT)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
