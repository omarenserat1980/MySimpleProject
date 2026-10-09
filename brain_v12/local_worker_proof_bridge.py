"""Bridge the Brain Home Server queue to the local allowlisted worker.

This adapter is intentionally single-shot: one invocation claims at most one
task, executes it through the existing local worker allowlist, and reports
the result back to Home Server so the existing ExecutionProof gate decides
whether the task becomes ACCEPTED.
"""
from __future__ import annotations

import platform
from typing import Any

from brain_v12.home_server import HomeServerStore
from brain_v12.local_worker.brain_local_worker import execute


def run_once(store: HomeServerStore, worker_id: str,
             capabilities: list[str] | None = None,
             lease_seconds: int = 60) -> dict[str, Any]:
    claim = store.claim(worker_id, lease_seconds, capabilities or [])
    if claim.get("status") != "TASK_AVAILABLE":
        return {"status": "IDLE", "worker_id": worker_id}

    task = claim["task"]
    try:
        evidence = execute(task["task"], task["params"])
        result = {
            "worker_id": worker_id,
            "host": {
                "hostname": platform.node(),
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
            },
            "execution": evidence,
        }
        return store.report(task["task_id"], worker_id, True, result, "")
    except Exception as exc:
        return store.report(task["task_id"], worker_id, False, {},
                            f"{type(exc).__name__}:{exc}")
