"""Bounded revenue guardian for an active Brain client.

The guardian observes one target client, distinguishes verified revenue from
mere activity/opportunities, identifies blockers, and can request one bounded
next action through the existing primary pipeline.

It never fabricates revenue, never treats opportunities as payments, and never
creates parallel workflows.
"""
from __future__ import annotations

from typing import Any, Callable


TARGET_CLIENT_ID = "CL-000003"
GUARDIAN_CLIENT_ID = "CL-000004"


class ClientRevenueGuardian:
    """Supervisory client focused on turning verified gaps into bounded action."""

    def __init__(
        self,
        activity_reader: Callable[[str], dict[str, Any]],
        revenue_reader: Callable[[str], dict[str, Any]],
        blocker_reader: Callable[[str], list[dict[str, Any]]] | None = None,
        action_requester: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
    ) -> None:
        self.activity_reader = activity_reader
        self.revenue_reader = revenue_reader
        self.blocker_reader = blocker_reader or (lambda _client_id: [])
        self.action_requester = action_requester

    def inspect(self, client_id: str = TARGET_CLIENT_ID) -> dict[str, Any]:
        client_id = str(client_id).strip()
        activity = self.activity_reader(client_id) or {}
        revenue = self.revenue_reader(client_id) or {}
        blockers = self.blocker_reader(client_id) or []

        verified = float(revenue.get("verified_revenue_jod", revenue.get("verified", 0)) or 0)
        opportunities = int(
            activity.get("opportunities", activity.get("opportunity_count", 0)) or 0
        )
        completed = int(activity.get("completed", activity.get("completed_count", 0)) or 0)

        if verified > 0:
            state = "REVENUE_VERIFIED"
            next_action = "MAINTAIN_AND_SCALE"
        elif blockers:
            state = "BLOCKED_BEFORE_REVENUE"
            next_action = "REMOVE_FIRST_BLOCKER"
        elif opportunities or completed:
            state = "ACTIVE_NO_VERIFIED_REVENUE"
            next_action = "INCREASE_CONVERSION_ACTIVITY"
        else:
            state = "INACTIVE_NO_VERIFIED_REVENUE"
            next_action = "START_ONE_REVENUE_PATH"

        return {
            "ok": True,
            "guardian_client_id": GUARDIAN_CLIENT_ID,
            "target_client_id": client_id,
            "state": state,
            "verified_revenue_jod": verified,
            "revenue_is_verified": verified > 0,
            "activity": activity,
            "revenue": revenue,
            "blockers": blockers,
            "recommendation": {
                "action": next_action,
                "reason": (
                    "Only verified payment evidence counts as revenue."
                    if verified <= 0
                    else "Verified payment exists; protect and improve the proven path."
                ),
            },
            "policy": {
                "one_active_request_per_client": True,
                "existing_primary_pipeline_only": True,
                "no_parallel_workflows": True,
                "no_revenue_without_payment_evidence": True,
            },
        }

    def deep_inspect(self, income_engine: Any, income_lifecycle: Any, client_id: str = TARGET_CLIENT_ID) -> dict[str, Any]:
        """Aggregate the existing income lifecycle without mutating it."""
        report = self.inspect(client_id)
        snapshot = income_engine.snapshot()
        lifecycle = income_lifecycle.summary()
        opportunities = list(snapshot.get("opportunities") or [])
        verified = float(snapshot.get("verified_revenue_jod", 0) or 0)
        active = [x for x in opportunities if str(x.get("status") or "").upper() not in {"STALE", "COMPLETED", "PAYMENT_VERIFIED"}]
        ready = [x for x in active if str(x.get("status") or "").upper() == "READY_TO_APPLY"]
        if verified > 0:
            priority = "PROTECT_AND_SCALE_VERIFIED_PATH"
        elif ready:
            priority = "CONVERT_READY_TO_APPLY_TO_SUBMITTED_WITH_EXTERNAL_EVIDENCE"
        elif active:
            priority = "ADVANCE_HIGHEST_FIT_ACTIVE_OPPORTUNITY"
        else:
            priority = "CREATE_FRESH_EVIDENCE_BACKED_OPPORTUNITY_PIPELINE"
        report["deep_audit"] = {
            "verified_revenue_jod": verified,
            "revenue_gap_exists": verified <= 0,
            "lifecycle_counts": dict(lifecycle.get("counts") or {}),
            "active_opportunities": len(active),
            "ready_to_apply": len(ready),
            "highest_priority": priority,
            "hard_gate": "PAYMENT_VERIFIED + payment_evidence",
            "evidence_chain": list(getattr(income_lifecycle, "ORDER", ())),
        }
        return report

    def nudge_once(self, client_id: str = TARGET_CLIENT_ID) -> dict[str, Any]:
        """Request at most one bounded action; execution remains elsewhere."""
        report = self.inspect(client_id)
        if report["state"] == "REVENUE_VERIFIED":
            return {**report, "nudged": False, "status": "NO_NUDGE_REQUIRED"}

        if self.action_requester is None:
            return {
                **report,
                "nudged": False,
                "status": "ACTION_REQUESTER_NOT_REGISTERED",
            }

        action = {
            "client_id": client_id,
            "objective": "MOVE_TOWARD_VERIFIED_REVENUE",
            "recommended_action": report["recommendation"]["action"],
            "blockers": report["blockers"],
            "constraint": "ONE_BOUNDED_ACTION_THROUGH_EXISTING_PRIMARY_PIPELINE",
        }
        result = self.action_requester(client_id, action)
        return {
            **report,
            "nudged": True,
            "status": "NUDGE_REQUESTED",
            "action_result": result if isinstance(result, dict) else {"result": result},
        }


def public_guardian_registry() -> dict[str, Any]:
    return {
        "ok": True,
        "guardian_client_id": GUARDIAN_CLIENT_ID,
        "target_client_id": TARGET_CLIENT_ID,
        "role": "REVENUE_ACTIVITY_GUARDIAN",
        "purpose": (
            "مراقبة أعمال CL-000003، التحقق من الإيراد الفعلي المثبت، "
            "كشف العوائق، ودفع مسار واحد محدود نحو الإيراد."
        ),
        "rules": {
            "verified_payment_only": True,
            "one_active_request_per_client": True,
            "no_parallel_workflows": True,
            "existing_primary_pipeline_only": True,
            "bounded_nudge": True,
        },
    }
