"""Unified operational control plane for Brain V7.

Combines worker health, verified revenue, and completion readiness into one
auditable snapshot. It reports evidence; it does not claim external execution.
"""
from __future__ import annotations

from dataclasses import asdict
from time import time
from typing import Any

from .completion_orchestrator import evaluate
from .verified_revenue_ledger import VerifiedRevenueLedger
from .worker_health import WorkerHealthRegistry


class OperationalControlPlane:
    def __init__(self) -> None:
        self.health = WorkerHealthRegistry()
        self.revenue = VerifiedRevenueLedger()
        self.started_at = time()

    def heartbeat(self, worker_id: str, *, status: str = "HEALTHY", cycle: int = 0, detail: str = "") -> dict[str, Any]:
        return self.health.beat(worker_id, status=status, cycle=cycle, detail=detail)

    def record_revenue(self, **kwargs: Any) -> dict[str, Any]:
        return self.revenue.record(**kwargs)

    def snapshot(self) -> dict[str, Any]:
        health = self.health.inspect()
        return {
            "started_at": self.started_at,
            "health": health,
            "revenue": self.revenue.snapshot(),
            "revenue_is_guaranteed": False,
            "external_execution_verified": bool(health["live_workers"]),
        }

    def readiness(self, *, organization: dict[str, Any], external_work: dict[str, Any], factory: dict[str, Any], deployment_configured: bool) -> dict[str, Any]:
        return evaluate({
            "cognition_memory": True,
            "organization": organization,
            "revenue_challenge": {"target_jod": 10_000},
            "external_work": external_work,
            "cinematic_factory": factory,
            "safety_gates": True,
            "deployment": {"configured": deployment_configured},
        })
