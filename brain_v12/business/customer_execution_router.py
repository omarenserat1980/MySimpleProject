"""Fail-closed routing contract for the two active customer activities.

The router does not perform side effects. It resolves a customer activity to
an existing Brain execution backend and refuses dispatch when that backend is
not explicitly available. This prevents a customer request from being marked
complete merely because a route exists.
"""
from __future__ import annotations

from typing import Any, Callable

from .two_customer_execution_contract import CUSTOMER_SCOPE, CustomerActivity, resolve_customer

BackendProbe = Callable[[], dict[str, Any]]


class CustomerExecutionRouter:
    def __init__(self, probes: dict[str, BackendProbe] | None = None) -> None:
        self.probes = dict(probes or {})

    def inspect(self, customer_id: str) -> dict[str, Any]:
        activity = resolve_customer(customer_id)
        probe = self.probes.get(activity.backend)
        if probe is None:
            return {
                "ok": False,
                "status": "BACKEND_NOT_REGISTERED",
                "customer_id": activity.customer_id,
                "activity_id": activity.activity_id,
                "backend": activity.backend,
                "dispatch_allowed": False,
            }
        try:
            readiness = probe()
        except Exception as exc:
            return {
                "ok": False,
                "status": "BACKEND_PROBE_FAILED",
                "customer_id": activity.customer_id,
                "activity_id": activity.activity_id,
                "backend": activity.backend,
                "dispatch_allowed": False,
                "error": f"{type(exc).__name__}:{exc}",
            }
        ready = isinstance(readiness, dict) and readiness.get("ready") is True
        return {
            "ok": ready,
            "status": "READY" if ready else "BACKEND_NOT_READY",
            "customer_id": activity.customer_id,
            "activity_id": activity.activity_id,
            "backend": activity.backend,
            "dispatch_allowed": ready,
            "readiness": readiness,
        }

    def build_plan(self, customer_id: str) -> dict[str, Any]:
        activity = resolve_customer(customer_id)
        inspection = self.inspect(customer_id)
        return {
            "customer_id": activity.customer_id,
            "activity_id": activity.activity_id,
            "objective": activity.objective,
            "backend": activity.backend,
            "inspection": inspection,
            "stages": [
                "INSPECT",
                "DIAGNOSE",
                "REPAIR_IF_REQUIRED",
                "RESUME",
                "VERIFY",
                "EVIDENCE",
            ],
            "dispatch_allowed": inspection["dispatch_allowed"],
            "completion_allowed": False,
        }

    def dispatch(
        self,
        customer_id: str,
        executor: Callable[[CustomerActivity], dict[str, Any]],
    ) -> dict[str, Any]:
        activity = resolve_customer(customer_id)
        inspection = self.inspect(customer_id)
        if not inspection["dispatch_allowed"]:
            return {
                "ok": False,
                "status": "DISPATCH_BLOCKED",
                "reason": inspection["status"],
                "customer_id": activity.customer_id,
                "activity_id": activity.activity_id,
            }
        result = executor(activity)
        if not isinstance(result, dict):
            return {
                "ok": False,
                "status": "EXECUTOR_INVALID_RESULT",
                "customer_id": activity.customer_id,
                "activity_id": activity.activity_id,
            }
        # This router deliberately never turns execution success into
        # completion. VerificationGate/BrainControlPlane must decide that.
        return {
            "ok": True,
            "status": "EXECUTED_AWAITING_VERIFICATION",
            "customer_id": activity.customer_id,
            "activity_id": activity.activity_id,
            "execution": result,
            "completion_allowed": False,
        }


def default_router() -> CustomerExecutionRouter:
    return CustomerExecutionRouter()
