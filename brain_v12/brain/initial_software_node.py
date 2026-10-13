"""Initial isolated software node for Electronic Brain.

This is a software-only control-plane prototype. It runs no shell commands,
contacts no physical host, opens no network listeners, and cannot boot Windows.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import time

from .software_node_hardware import SoftwareNodeHardware

SCHEMA = "electronic-brain.initial-software-node.v1"
NODE_ID = "brain-software-node-01"
ALLOWED_TASKS = frozenset({"health_check", "write_text", "read_text", "run_brainvm", "network_self_test"})


class InitialSoftwareNode:
    """Small sandboxed node lifecycle and allowlisted task executor."""

    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.hardware = SoftwareNodeHardware(self.root)
        self.state = "STOPPED"
        self.started_at: float | None = None
        self.heartbeat_count = 0
        self.completed_tasks = 0

    def start(self) -> dict[str, Any]:
        self.state = "READY_SIMULATED"
        self.started_at = time.time()
        return self.status()

    def stop(self) -> dict[str, Any]:
        self.state = "STOPPED"
        return self.status()

    def status(self) -> dict[str, Any]:
        return {
            "ok": self.state == "READY_SIMULATED",
            "schema": SCHEMA,
            "node_id": NODE_ID,
            "node_type": "SOFTWARE_ONLY",
            "state": self.state,
            "execution_mode": "SANDBOXED_SOFTWARE_TASKS",
            "physical_hardware_required": False,
            "physical_host_contacted": False,
            "network_io_enabled": False,
            "shell_execution_enabled": False,
            "external_resources_created": False,
            "windows_server_2025_boot_verified": False,
            "real_boot_eligible": False,
            "heartbeat_count": self.heartbeat_count,
            "completed_tasks": self.completed_tasks,
            "workspace": str(self.root),
            "hardware": self.hardware.status(),
        }

    def heartbeat(self) -> dict[str, Any]:
        if self.state != "READY_SIMULATED":
            return {"ok": False, "status": "NODE_NOT_READY", "node_id": NODE_ID}
        self.heartbeat_count += 1
        return {
            "ok": True,
            "status": "HEARTBEAT_OK",
            "node_id": NODE_ID,
            "sequence": self.heartbeat_count,
            "execution_mode": "SANDBOXED_SOFTWARE_TASKS",
        }

    def _safe_path(self, relative_path: str) -> Path:
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise ValueError("INVALID_PATH")
        candidate = (self.root / relative_path).resolve()
        if not candidate.is_relative_to(self.root):
            raise ValueError("PATH_OUTSIDE_WORKSPACE")
        return candidate

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        if self.state != "READY_SIMULATED":
            return {"ok": False, "status": "NODE_NOT_READY", "node_id": NODE_ID}
        if not isinstance(task, dict):
            return {"ok": False, "status": "INVALID_TASK"}
        kind = task.get("type")
        if kind not in ALLOWED_TASKS:
            return {
                "ok": False,
                "status": "TASK_TYPE_NOT_ALLOWED",
                "allowed_task_types": sorted(ALLOWED_TASKS),
                "node_id": NODE_ID,
            }

        try:
            if kind == "health_check":
                result: dict[str, Any] = {"health": "OK", "state": self.state}
            elif kind == "write_text":
                result = self.hardware.write_text(task.get("path"), task.get("content"))
            elif kind == "read_text":
                result = self.hardware.read_text(task.get("path"))
            elif kind == "run_brainvm":
                result = self.hardware.run_program(task.get("program"), max_cycles=task.get("max_cycles", 10000))
            else:  # network_self_test
                result = self.hardware.network_self_test()

        except (OSError, ValueError, IndexError, RuntimeError) as exc:
            message = str(exc)
            if isinstance(exc, OSError):
                message = "WORKSPACE_IO_ERROR"
            return {"ok": False, "status": message, "node_id": NODE_ID}

        self.completed_tasks += 1
        return {
            "ok": True,
            "status": "TASK_COMPLETED",
            "node_id": NODE_ID,
            "task_type": kind,
            "execution_mode": "SANDBOXED_SOFTWARE_TASKS",
            "result": result,
            "real_windows_boot_verified": False,
        }
