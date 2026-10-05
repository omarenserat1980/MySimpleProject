#!/usr/bin/env python3
"""Queue a Brain local verification job for the Brain-owned local worker."""
from __future__ import annotations
import json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "brain6_artifacts" / "local_worker" / "queued"

def main():
    QUEUE.mkdir(parents=True, exist_ok=True)
    job_id = f"brain-local-verification-{int(time.time())}"
    path = QUEUE / f"{job_id}.json"
    payload = {
        "job_id": job_id,
        "task": "brain_local_verification",
        "params": {},
        "submitted_by": "brain-control-plane",
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"queued": True, "job_id": job_id, "path": str(path)}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
