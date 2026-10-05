#!/usr/bin/env python3
"""Self-contained Brain Local Worker execution/recovery proof.

Starts a real worker subprocess, submits an allowlisted task, verifies durable
completion evidence, then simulates an abandoned running job and proves that
the worker recovers it and executes it after restart.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKER = [sys.executable, "-m", "brain_v12.local_worker.brain_local_worker"]


def wait_for(path: Path, timeout: float = 30.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        if path.exists():
            return True
        time.sleep(0.25)
    return False


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="brain-worker-selftest-") as td:
        root = Path(td) / "worker"
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        env["BRAIN_LOCAL_WORKER_ROOT"] = str(root)
        env["BRAIN_WORKER_ID"] = "brain-selftest"
        env["BRAIN_LOCAL_WORKER_POLL_SECONDS"] = "0.25"
        env["BRAIN_LOCAL_WORKER_RECOVERY_TTL_SECONDS"] = "1"

        proc = subprocess.Popen(
            WORKER, cwd=ROOT, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True
        )
        try:
            queued = root / "queued"
            completed = root / "completed"
            failed = root / "failed"
            running = root / "running"
            for p in (queued, completed, failed, running):
                if not wait_for(p, 10):
                    raise RuntimeError(f"worker_directory_not_ready:{p}")

            job = queued / "selftest-python.json"
            job.write_text(json.dumps({
                "job_id": "selftest-python",
                "task": "python_version",
                "params": {},
            }), encoding="utf-8")

            result = completed / job.name
            if not wait_for(result):
                raise RuntimeError("worker_execution_timeout")
            evidence = json.loads(result.read_text(encoding="utf-8"))
            if evidence.get("status") != "VERIFIED":
                raise RuntimeError(f"worker_execution_not_verified:{evidence}")

            proc.terminate()
            proc.wait(timeout=5)

            abandoned = running / "recovery-selftest.json"
            abandoned.write_text(json.dumps({
                "job_id": "recovery-selftest",
                "task": "python_version",
                "params": {},
            }), encoding="utf-8")
            old = time.time() - 10
            os.utime(abandoned, (old, old))

            proc = subprocess.Popen(
                WORKER, cwd=ROOT, env=env,
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True
            )
            recovered = queued / abandoned.name
            recovered_result = completed / abandoned.name
            if not wait_for(recovered, 10) and not wait_for(recovered_result, 10):
                raise RuntimeError("recovery_queue_timeout")
            if not wait_for(recovered_result, 20):
                raise RuntimeError("recovery_execution_timeout")
            recovered_evidence = json.loads(recovered_result.read_text(encoding="utf-8"))
            if recovered_evidence.get("status") != "VERIFIED":
                raise RuntimeError(f"recovered_execution_not_verified:{recovered_evidence}")

            report = {
                "schema": "brain.local_worker_selftest.v1",
                "status": "PASS",
                "execution": "real_worker_subprocess",
                "queue_to_completed": True,
                "restart_recovery_to_completed": True,
                "worker_id": "brain-selftest",
            }
            print(json.dumps(report, indent=2))
            return 0
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
