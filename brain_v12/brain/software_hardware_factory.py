"""Bounded logical hardware leases with a verifiable, built-in local execution probe.

This manager does not manufacture physical CPU/RAM/GPU. Leases reserve a conservative
logical budget against measurements of the Brain host; the built-in probe executes
a fixed, bounded workload inside the Brain process. It never accepts arbitrary code.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import os
import platform
import shutil
import socket
import threading
import time
from typing import Any
from uuid import uuid4

from .device_cloud_pool import local_host_node


@dataclass
class ResourceLease:
    lease_id: str
    task_id: str
    executor_id: str
    cpu_cores_logical: float
    memory_mb_logical: int
    disk_mb_logical: int
    status: str
    created_at: float
    source: str = "brain_host_measurement"
    resource_kind: str = "LOGICAL_LEASE_NOT_PHYSICAL_HARDWARE"

    def public(self) -> dict[str, Any]:
        return asdict(self)


class SoftwareHardwareFactory:
    """In-memory, process-local leases and bounded built-in test jobs."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._leases: dict[str, ResourceLease] = {}
        self._jobs: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _capacity() -> dict[str, Any]:
        node = local_host_node()
        # Deliberately conservative logical pool, not the full host capacity.
        cpu_budget = max(0.25, round(node.cpu_cores * 0.50, 2)) if node.cpu_cores else 0.0
        memory_budget = int(node.memory_mb * 0.25)
        disk_budget = int(node.disk_mb * 0.10)
        return {
            "executor_id": node.node_id,
            "platform": node.platform,
            "cpu_cores_physical_observed": node.cpu_cores,
            "memory_mb_physical_total_observed": node.memory_mb,
            "disk_mb_free_observed": node.disk_mb,
            "cpu_cores_logical_budget": cpu_budget,
            "memory_mb_logical_budget": memory_budget,
            "disk_mb_logical_budget": disk_budget,
            "gpu_count_observed": 0,
            "gpu_status": "NOT_MEASURED_NO_GPU_CLAIM",
            "source": node.source,
            "observed": node.observed,
        }

    def status(self) -> dict[str, Any]:
        capacity = self._capacity()
        with self._lock:
            active = [lease for lease in self._leases.values() if lease.status == "ALLOCATED"]
            used_cpu = sum(item.cpu_cores_logical for item in active)
            used_memory = sum(item.memory_mb_logical for item in active)
            used_disk = sum(item.disk_mb_logical for item in active)
            return {
                "ok": True,
                "factory": "BRAIN_SOFTWARE_DEFINED_HARDWARE",
                "execution_host": capacity["executor_id"],
                "execution_platform": capacity["platform"],
                "resource_semantics": "logical quotas backed by measured host; not additional physical hardware",
                "capacity": capacity,
                "allocated": {
                    "cpu_cores_logical": round(used_cpu, 2),
                    "memory_mb_logical": used_memory,
                    "disk_mb_logical": used_disk,
                    "active_leases": len(active),
                },
                "remaining": {
                    "cpu_cores_logical": round(max(0.0, capacity["cpu_cores_logical_budget"] - used_cpu), 2),
                    "memory_mb_logical": max(0, capacity["memory_mb_logical_budget"] - used_memory),
                    "disk_mb_logical": max(0, capacity["disk_mb_logical_budget"] - used_disk),
                },
                "lease_storage": "in_memory_non_durable",
                "remote_execution_proven": False,
            }

    def resources(self) -> dict[str, Any]:
        result = self.status()
        with self._lock:
            result["leases"] = [lease.public() for lease in self._leases.values()]
            result["jobs"] = list(self._jobs.values())
        return result

    def plan(self, *, task_id: str, cpu_cores: float, memory_mb: int, disk_mb: int) -> dict[str, Any]:
        if not task_id.strip():
            raise ValueError("task_id is required")
        if cpu_cores <= 0 or memory_mb <= 0 or disk_mb < 0:
            raise ValueError("cpu_cores and memory_mb must be positive; disk_mb cannot be negative")
        state = self.status()
        remaining = state["remaining"]
        accepted = (
            cpu_cores <= remaining["cpu_cores_logical"]
            and memory_mb <= remaining["memory_mb_logical"]
            and disk_mb <= remaining["disk_mb_logical"]
        )
        return {
            "status": "PLANNED" if accepted else "BLOCKED_INSUFFICIENT_LOGICAL_CAPACITY",
            "task_id": task_id,
            "executor_id": state["execution_host"],
            "demand": {"cpu_cores_logical": cpu_cores, "memory_mb_logical": memory_mb, "disk_mb_logical": disk_mb},
            "resource_semantics": "logical lease only; no physical hardware is created",
            "execution_started": False,
        }

    def allocate(self, *, task_id: str, cpu_cores: float, memory_mb: int, disk_mb: int) -> dict[str, Any]:
        with self._lock:
            plan = self.plan(task_id=task_id, cpu_cores=cpu_cores, memory_mb=memory_mb, disk_mb=disk_mb)
            if plan["status"] != "PLANNED":
                raise ValueError(plan["status"])
            lease = ResourceLease(
                lease_id="lease-" + uuid4().hex,
                task_id=task_id,
                executor_id=str(plan["executor_id"]),
                cpu_cores_logical=float(cpu_cores),
                memory_mb_logical=int(memory_mb),
                disk_mb_logical=int(disk_mb),
                status="ALLOCATED",
                created_at=time.time(),
            )
            self._leases[lease.lease_id] = lease
            return {"ok": True, "lease": lease.public(), "resource_semantics": "logical lease; not OS-enforced RAM/CPU isolation"}

    def release(self, lease_id: str) -> dict[str, Any]:
        with self._lock:
            lease = self._leases.get(lease_id)
            if lease is None:
                raise KeyError("LEASE_NOT_FOUND")
            if lease.status == "RELEASED":
                return {"ok": True, "lease": lease.public(), "idempotent": True}
            lease.status = "RELEASED"
            return {"ok": True, "lease": lease.public(), "idempotent": False}

    def run_self_test(self, lease_id: str, *, rounds: int = 1000) -> dict[str, Any]:
        """Execute a deterministic, bounded SHA-256 workload; no arbitrary command/code."""
        if not 1 <= rounds <= 100_000:
            raise ValueError("rounds must be between 1 and 100000")
        with self._lock:
            lease = self._leases.get(lease_id)
            if lease is None or lease.status != "ALLOCATED":
                raise ValueError("ACTIVE_LEASE_REQUIRED")
            job_id = "job-" + uuid4().hex
            job = {
                "job_id": job_id,
                "lease_id": lease_id,
                "task_id": lease.task_id,
                "status": "RUNNING",
                "executor_id": lease.executor_id,
                "execution_location": "brain_host_process",
                "started_at": time.time(),
                "workload": "fixed_sha256_self_test",
                "rounds": rounds,
            }
            self._jobs[job_id] = job

        started = time.perf_counter()
        digest = b"electronic-brain-hardware-probe"
        for index in range(rounds):
            digest = hashlib.sha256(digest + index.to_bytes(4, "big")).digest()
        elapsed = time.perf_counter() - started
        with self._lock:
            job.update({
                "status": "SUCCEEDED",
                "finished_at": time.time(),
                "duration_seconds": round(elapsed, 6),
                "result_sha256": digest.hex(),
                "process_id": os.getpid(),
                "host_platform": platform.platform(),
                "evidence": "built_in_workload_completed_and_digest_recorded",
            })
            return {"ok": True, "job": dict(job)}

    def job(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            value = self._jobs.get(job_id)
            if value is None:
                raise KeyError("JOB_NOT_FOUND")
            return dict(value)
