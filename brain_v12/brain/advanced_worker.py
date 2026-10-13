"""Fail-closed advanced Brain worker lifecycle and task-admission policy.

This module is a control-plane primitive, not a process launcher. Admission is
not execution, and execution is not proof of guest boot. Real boot tasks require
an explicitly configured real-executor worker and fresh, independently verified
gates; simulation workers can never admit real-boot tasks.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any, Callable, Mapping

REAL_BOOT_CAPABILITY = "windows-server-2025-real-boot"
REAL_BOOT_GATES = (
    "host_identity_verified",
    "kvm_runtime_verified",
    "executor_attestation_verified",
    "execution_contract_verified",
    "owner_authorized",
    "source_commit_matches",
)


@dataclass
class WorkerState:
    worker_id: str
    mode: str
    capabilities: frozenset[str]
    lease_seconds: int
    registered_at: float | None = None
    last_heartbeat: float | None = None
    lease_until: float = 0.0
    health: str = "NEW"
    host_facts: dict[str, Any] = field(default_factory=dict)
    heartbeat_count: int = 0


class AdvancedWorker:
    """Lease-based worker state machine with explicit simulator/real isolation."""

    def __init__(
        self,
        worker_id: str,
        capabilities=(),
        *,
        mode: str = "simulator",
        lease_seconds: int = 30,
        clock: Callable[[], float] = time.time,
    ):
        worker_id = str(worker_id).strip()
        if not worker_id:
            raise ValueError("WORKER_ID_REQUIRED")
        mode = str(mode).strip().lower()
        if mode not in {"simulator", "real_executor"}:
            raise ValueError("WORKER_MODE_INVALID")
        caps = frozenset(str(c).strip() for c in capabilities if str(c).strip())
        if mode == "simulator" and REAL_BOOT_CAPABILITY in caps:
            raise ValueError("SIMULATOR_CANNOT_ADVERTISE_REAL_BOOT")
        self._clock = clock
        self.state = WorkerState(
            worker_id=worker_id,
            mode=mode,
            capabilities=caps,
            lease_seconds=max(5, min(int(lease_seconds), 300)),
        )

    def register(self, *, host_facts: Mapping[str, Any] | None = None,
                 now: float | None = None) -> dict[str, Any]:
        now = self._now(now)
        self.state.registered_at = now
        self.state.host_facts = dict(host_facts or {})
        self.state.health = "HEALTHY"
        self.state.last_heartbeat = now
        self.state.lease_until = now + self.state.lease_seconds
        self.state.heartbeat_count = 1
        return self.snapshot(now=now)

    def heartbeat(self, *, host_facts: Mapping[str, Any] | None = None,
                  now: float | None = None) -> dict[str, Any]:
        now = self._now(now)
        if self.state.registered_at is None:
            raise RuntimeError("WORKER_NOT_REGISTERED")
        if now > self.state.lease_until:
            self.state.health = "LEASE_EXPIRED"
            raise RuntimeError("WORKER_LEASE_EXPIRED_RE_REGISTER_REQUIRED")
        if host_facts is not None:
            # Replace, do not merge, so stale positive facts cannot survive a
            # fresh failed probe by being omitted from the new observation.
            self.state.host_facts = dict(host_facts)
        self.state.last_heartbeat = now
        self.state.lease_until = now + self.state.lease_seconds
        self.state.heartbeat_count += 1
        self.state.health = "HEALTHY"
        return self.snapshot(now=now)

    def snapshot(self, *, now: float | None = None) -> dict[str, Any]:
        now = self._now(now)
        registered = self.state.registered_at is not None
        live = registered and now <= self.state.lease_until and self.state.health == "HEALTHY"
        return {
            "schema": "brain.advanced-worker.v1",
            "worker_id": self.state.worker_id,
            "mode": self.state.mode,
            "capabilities": sorted(self.state.capabilities),
            "registered": registered,
            "online": live,
            "health": self.state.health if live else ("LEASE_EXPIRED" if registered else "NOT_REGISTERED"),
            "lease_until": self.state.lease_until if registered else None,
            "heartbeat_count": self.state.heartbeat_count,
            # Do not expose last-heartbeat timestamps in the public snapshot.
            "execution_claim": "NONE",
            "windows_boot_verified": False,
        }

    def admit_task(self, task: Mapping[str, Any], *, now: float | None = None) -> dict[str, Any]:
        """Evaluate policy only; never executes the task or marks boot successful."""
        now = self._now(now)
        snap = self.snapshot(now=now)
        reasons: list[str] = []
        capability = str(task.get("capability", "")).strip()
        task_id = str(task.get("task_id", "")).strip()
        if not task_id:
            reasons.append("TASK_ID_REQUIRED")
        if not snap["online"]:
            reasons.append("WORKER_NOT_LIVE")
        if capability not in self.state.capabilities:
            reasons.append("CAPABILITY_NOT_ADVERTISED")
        if capability == REAL_BOOT_CAPABILITY:
            if self.state.mode != "real_executor":
                reasons.append("REAL_BOOT_REQUIRES_REAL_EXECUTOR")
            for gate in REAL_BOOT_GATES:
                if self.state.host_facts.get(gate) is not True:
                    reasons.append(f"{gate.upper()}_NOT_VERIFIED")
        return {
            "schema": "brain.advanced-worker-admission.v1",
            "worker_id": self.state.worker_id,
            "task_id": task_id or None,
            "capability": capability or None,
            "admitted": not reasons,
            "reasons": reasons,
            "decision": "ADMISSION_ONLY_NOT_EXECUTED" if not reasons else "DENIED",
            "windows_boot_verified": False,
        }

    def _now(self, value: float | None) -> float:
        return float(self._clock() if value is None else value)
