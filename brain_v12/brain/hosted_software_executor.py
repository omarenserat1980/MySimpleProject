"""Ephemeral GitHub-hosted software executor adapter.

This is a replacement for Arkan-dependent *software CI tasks only*. It uses
Brain's existing allowlisted symbolic executor and always reports SIMULATED.
It is not a persistent worker and cannot prove or perform native Windows boot.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from .arkan_software_executor import ArkanSoftwareExecutor


def default_root() -> Path:
    configured = os.getenv("BRAIN_HOSTED_EXECUTOR_ROOT", "").strip()
    if configured:
        return Path(configured).expanduser()
    # GitHub-hosted runners are ephemeral; keep state inside the current job.
    return Path(os.getenv("RUNNER_TEMP", "/tmp")) / "brain-hosted-software-executor"


class HostedSoftwareExecutor(ArkanSoftwareExecutor):
    """Hosted CI adapter with a distinct identity and explicit ephemeral boundary."""

    def __init__(self, root: str | Path | None = None, *, workers: int = 1,
                 maintenance_interval: float = 0.25):
        super().__init__(root or default_root(), workers=workers,
                         maintenance_interval=maintenance_interval)

    def _snapshot(self, service_state: str | None = None) -> dict[str, Any]:
        snapshot = super()._snapshot(service_state)
        snapshot["schema"] = "brain.hosted-software-executor.v1"
        snapshot["node"] = {
            "name": "Brain Hosted Software Executor",
            "id": "brain-hosted-ci-01",
            "backend": "github-hosted-runner",
        }
        snapshot["runtime_mode"] = "EPHEMERAL_CI_JOB"
        snapshot["persistence"] = "JOB_LOCAL_SQLITE"
        snapshot["reality"] = "SIMULATED"
        snapshot["physical_host_required"] = False
        snapshot["desktop_commander_required"] = False
        snapshot["host_binding"] = None
        snapshot["host_resources_allocated"] = False
        snapshot["windows_server_2025"] = {
            "installation_status": "NOT_INSTALLED",
            "boot_status": "NOT_VERIFIED",
            "native_os_boot_verified": False,
        }
        return snapshot


def run_bounded_task(task_type: str, *, timeout_seconds: float = 20.0) -> dict[str, Any]:
    """Run only the inherited allowlisted symbolic task and return truthful evidence."""
    executor = HostedSoftwareExecutor()
    try:
        executor.start()
        task = executor.submit(task_type, idempotency_key=f"hosted-ci-{task_type}")
        deadline = time.monotonic() + max(1.0, timeout_seconds)
        while time.monotonic() < deadline:
            result = executor.task_status(task["task_id"])
            state = result.get("task", {}).get("status")
            if state in {"COMPLETED", "FAILED", "REJECTED"}:
                report = executor.status()
                report["task"] = result.get("task")
                report["ok"] = state == "COMPLETED"
                return report
            time.sleep(0.1)
        report = executor.status()
        report.update({"ok": False, "failure_reason": "TASK_TIMEOUT",
                       "task_id": task["task_id"]})
        return report
    finally:
        executor.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-type", choices=("cpu_smoke", "self_test"), default="cpu_smoke")
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    args = parser.parse_args()
    report = run_bounded_task(args.task_type, timeout_seconds=args.timeout_seconds)
    print(json.dumps(report, sort_keys=True))
    return 0 if report.get("ok") and report.get("reality") == "SIMULATED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
