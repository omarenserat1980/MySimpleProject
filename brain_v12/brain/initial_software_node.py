"""Initial isolated software node for Electronic Brain.

This is a software-only control-plane prototype. It runs no shell commands,
contacts no physical host, opens no network listeners, and cannot boot Windows.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import time

SCHEMA = "electronic-brain.initial-software-node.v1"
NODE_ID = "brain-software-node-01"
ALLOWED_TASKS = frozenset({"health_check", "write_text", "read_text"})


class InitialSoftwareNode:
    """Small sandboxed node lifecycle and allowlisted task executor."""

    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
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
                path = self._safe_path(task.get("path"))
                content = task.get("content")
                if not isinstance(content, str):
                    return {"ok": False, "status": "INVALID_CONTENT", "node_id": NODE_ID}
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                result = {"path": str(path.relative_to(self.root)), "bytes_written": len(content.encode("utf-8"))}
            else:  # read_text
                path = self._safe_path(task.get("path"))
                if not path.is_file():
                    return {"ok": False, "status": "FILE_NOT_FOUND", "node_id": NODE_ID}
                result = {"path": str(path.relative_to(self.root)), "content": path.read_text(encoding="utf-8")}

        except (OSError, ValueError) as exc:
            return {"ok": False, "status": str(exc) if isinstance(exc, ValueError) else "WORKSPACE_IO_ERROR", "node_id": NODE_ID}

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
