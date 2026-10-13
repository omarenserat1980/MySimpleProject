"""Brain 3 shared-memory bridge for a cloud-worker integration.

This is the in-process contract and safety boundary, not a network client and not
proof that a remote cloud worker is connected. A future authenticated transport
must call this bridge only after identity/authorization checks and must preserve
the same fail-closed action policy.
"""
from __future__ import annotations

import re
from typing import Any

from .unified_kernel import ALLOWED_ACTIONS, UnifiedBrainKernel


_WORKER_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$")
_ALLOWED_OUTCOMES = frozenset({"completed", "failed", "needs_review"})


class CloudWorkerMemoryBridge:
    """Expose Brain 3 memory and safe task metadata to a worker through one kernel."""

    def __init__(self, kernel: UnifiedBrainKernel, worker_id: str):
        if not isinstance(worker_id, str) or not _WORKER_ID.fullmatch(worker_id):
            raise ValueError("worker_id must be 1-64 safe identifier characters")
        self.kernel = kernel
        self.worker_id = worker_id

    @property
    def prefix(self) -> str:
        return f"cloud_worker:{self.worker_id}:"

    def status(self) -> dict[str, Any]:
        """Describe the local bridge honestly; never infer remote connectivity."""
        return {
            "worker_id": self.worker_id,
            "memory_backend": "brain3_shared_kernel",
            "shared_memory": True,
            "shared_task_queue": True,
            "transport": "in_process_only",
            "cloud_connected": False,
            "authenticated_remote_identity": False,
            "allowed_actions": sorted(ALLOWED_ACTIONS),
            "production_ready": False,
        }

    def read_context(self, prefix: str = "brain:context:") -> dict[str, Any]:
        """Read Brain-owned context only; worker-private memory is not implicit."""
        if not isinstance(prefix, str) or len(prefix) > 256:
            raise ValueError("context prefix must be a string of at most 256 characters")
        return {key: value for key, value in self.kernel.memory_items(prefix=prefix)}

    def submit_task(
        self, action: str, description: str, requested_by: str = "cloud_worker"
    ) -> dict[str, Any]:
        """Queue safe work in Brain's shared queue; never execute it on submission."""
        if requested_by != "cloud_worker":
            raise PermissionError("worker cannot impersonate another task source")
        task = self.kernel.submit(action, description, requested_by=f"cloud_worker:{self.worker_id}")
        self.kernel.memory_set(
            f"{self.prefix}task:{task['id']}",
            {"task_id": task["id"], "action": task["action"], "state": "QUEUED"},
        )
        return task

    def record_result(
        self,
        task_id: int,
        outcome: str,
        evidence: dict[str, Any],
        *,
        verified: bool = False,
    ) -> dict[str, Any]:
        """Write worker evidence into Brain memory without self-certifying success."""
        if not isinstance(task_id, int) or isinstance(task_id, bool) or task_id < 1:
            raise ValueError("task_id must be a positive integer")
        if outcome not in _ALLOWED_OUTCOMES:
            raise ValueError("outcome must be completed, failed, or needs_review")
        if not isinstance(evidence, dict):
            raise TypeError("evidence must be a dictionary")
        if verified is not False:
            raise PermissionError("workers cannot self-verify evidence; Brain verification is required")
        task = next((item for item in self.kernel.tasks() if item["id"] == task_id), None)
        if task is None:
            raise KeyError("task is not present in Brain's shared queue")
        if task.get("requested_by") != f"cloud_worker:{self.worker_id}":
            raise PermissionError("worker may only report against its own queued tasks")
        record = {
            "schema": "brain3.cloud-worker-evidence.v1",
            "worker_id": self.worker_id,
            "task_id": task_id,
            "outcome": outcome,
            "evidence": evidence,
            "worker_claimed_verified": False,
            "verified_by_brain": False,
            "cloud_connected": False,
            "windows_boot_verified": False,
        }
        self.kernel.memory_set(f"{self.prefix}evidence:{task_id}", record)
        self.kernel.memory_set(
            f"{self.prefix}task:{task_id}",
            {"task_id": task_id, "action": task["action"], "state": "EVIDENCE_RECORDED"},
        )
        return dict(record)

    def evidence_for(self, task_id: int) -> dict[str, Any] | None:
        """Retrieve evidence from the same Brain memory ledger."""
        value = self.kernel.memory_get(f"{self.prefix}evidence:{task_id}")
        return dict(value) if isinstance(value, dict) else None
