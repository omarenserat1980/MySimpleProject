"""Persistent, software-only Arkan task executor.

Only predefined symbolic CPU workloads are accepted. This service never invokes a
shell, probes a physical host, or claims that a native guest OS has booted.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Any

from ..blade_server import BladeChassis
from ..virtual_hardware.arkan_provisioner import ARKAN_ID
from .resource_manager import ResourceManager
from .virtual_task_queue import VirtualTaskQueue

SCHEMA = "brain.arkan.software-executor.v1"
WORKLOADS: dict[str, list[tuple[Any, ...]]] = {
    "cpu_smoke": [("MOVI", 0, 2025), ("OUT", 0), ("HALT",)],
    "self_test": [("MOVI", 0, 42), ("OUT", 0), ("HALT",)],
}


def default_root() -> Path:
    explicit = os.getenv("BRAIN_ARKAN_SOFTWARE_ROOT")
    if explicit:
        return Path(explicit).expanduser()
    runtime_home = Path(os.getenv("BRAIN_RUNTIME_HOME", "~/.brain/runtime")).expanduser()
    return runtime_home / "arkan-software-node"


class ArkanSoftwareExecutor:
    """Single-process worker using Brain's existing SQLite durable task queue."""

    def __init__(self, root: str | Path | None = None, *, workers: int = 1,
                 maintenance_interval: float = 1.0):
        self.root = Path(root).expanduser() if root is not None else default_root()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "tasks.sqlite3"
        self.state_path = self.root / "state.json"
        self.maintenance_interval = max(0.25, float(maintenance_interval))
        self.chassis = BladeChassis()
        self.resources = ResourceManager()
        self.queue = VirtualTaskQueue(
            self.chassis, self.resources, max_workers=max(1, int(workers)),
            store_path=self.db_path,
        )
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._started_at = time.time()
        self._last_heartbeat = self._started_at
        self._persist_state("READY")

    def submit(self, task_type: str, *, idempotency_key: str | None = None,
               task_id: str | None = None) -> dict[str, Any]:
        """Enqueue a predefined workload; arbitrary code and shell commands are rejected."""
        if task_type not in WORKLOADS:
            raise ValueError("TASK_TYPE_NOT_ALLOWED")
        task = self.queue.submit(
            list(WORKLOADS[task_type]),
            required_capabilities={"cpu"},
            task_id=task_id,
            idempotency_key=idempotency_key,
            priority="NORMAL",
        )
        self._persist_state("RUNNING")
        return self._task_dict(task)

    def task_status(self, task_id: str) -> dict[str, Any]:
        task = self.queue.get(task_id)
        if task is None:
            return {"ok": False, "status": "TASK_NOT_FOUND", "task_id": task_id}
        return {"ok": True, "task": self._task_dict(task)}

    @staticmethod
    def _task_dict(task: Any) -> dict[str, Any]:
        return {
            "task_id": task.task_id,
            "status": task.status,
            "attempt": task.attempt,
            "idempotency_key": task.idempotency_key,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "finished_at": task.finished_at,
            "result": task.result,
            "reality": "SIMULATED",
        }

    def _snapshot(self, service_state: str | None = None) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "node": {"name": "Arkan", "id": ARKAN_ID, "backend": "brain-simulator"},
            "service_state": service_state or ("RUNNING" if self._thread and self._thread.is_alive() else "READY"),
            "runtime_mode": "PROCESS_LOCAL",
            "persistence": "SQLITE_LOCAL_DISK",
            "root": str(self.root),
            "database": str(self.db_path),
            "queue": self.queue.status(),
            "last_heartbeat": self._last_heartbeat,
            "uptime_seconds": max(0.0, time.time() - self._started_at),
            "reality": "SIMULATED",
            "physical_host_required": False,
            "desktop_commander_required": False,
            "host_binding": None,
            "host_resources_allocated": False,
            "windows_server_2025": {
                "installation_status": "NOT_INSTALLED",
                "boot_status": "NOT_VERIFIED",
                "native_os_boot_verified": False,
            },
        }

    def _persist_state(self, service_state: str | None = None) -> dict[str, Any]:
        self._last_heartbeat = time.time()
        snapshot = self._snapshot(service_state)
        temporary = self.state_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, self.state_path)
        return snapshot

    def status(self) -> dict[str, Any]:
        return self._persist_state()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._maintenance_loop, name="arkan-software-maintenance", daemon=True)
        self._thread.start()
        self._persist_state("RUNNING")

    def _maintenance_loop(self) -> None:
        while not self._stop.wait(self.maintenance_interval):
            try:
                self.queue.recover_expired()
                self.queue.pump()
                self._persist_state("RUNNING")
            except Exception as exc:
                # Keep the service alive and record a bounded diagnostic, never fake health.
                self._last_heartbeat = time.time()
                snapshot = self._snapshot("DEGRADED")
                snapshot["last_error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
                temporary = self.state_path.with_suffix(".json.tmp")
                temporary.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                os.replace(temporary, self.state_path)

    def serve_forever(self) -> None:
        self.start()
        try:
            while not self._stop.wait(1.0):
                pass
        finally:
            self.close()

    def request_stop(self) -> None:
        self._stop.set()

    def close(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=max(1.0, self.maintenance_interval * 2))
        try:
            self._persist_state("STOPPED")
        finally:
            self.queue.shutdown()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("serve", "status", "submit"))
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--task-type", choices=tuple(WORKLOADS), default="cpu_smoke")
    parser.add_argument("--task-id", default=None)
    parser.add_argument("--idempotency-key", default=None)
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args(argv)

    service = ArkanSoftwareExecutor(args.root)
    if args.command == "status":
        try:
            print(json.dumps(service.status(), indent=2, sort_keys=True))
            return 0
        finally:
            service.close()

    if args.command == "submit":
        try:
            task = service.submit(args.task_type, task_id=args.task_id, idempotency_key=args.idempotency_key)
            task_id = task["task_id"]
            deadline = time.time() + max(0.1, args.timeout)
            while time.time() < deadline:
                result = service.task_status(task_id)
                current = result.get("task", {})
                if current.get("status") in {"COMPLETED", "FAILED"}:
                    print(json.dumps({"submission": task, "final": result, "service": service.status()},
                                     indent=2, sort_keys=True))
                    return 0 if current["status"] == "COMPLETED" else 1
                time.sleep(0.05)
            print(json.dumps({"ok": False, "status": "TASK_TIMEOUT", "task_id": task_id,
                              "service": service.status()}, indent=2, sort_keys=True))
            return 2
        finally:
            service.close()

    def stop_handler(_signum: int, _frame: Any) -> None:
        service.request_stop()

    signal.signal(signal.SIGTERM, stop_handler)
    signal.signal(signal.SIGINT, stop_handler)
    service.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
