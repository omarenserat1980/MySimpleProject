from threading import Lock
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


def _guardian_advance_lock(method):
    def wrapped(self, income_engine, income_lifecycle, client_id=TARGET_CLIENT_ID):
        with self._advance_lock:
            return method(self, income_engine, income_lifecycle, client_id)
    return wrapped


class ClientRevenueGuardian:
    _advance_lock = Lock()
    """Supervisory client focused on turning verified gaps into bounded action."""

    def __init__(
        self,
        activity_reader: Callable[[str], dict[str, Any]],
        revenue_reader: Callable[[str], dict[str, Any]],
        blocker_reader: Callable[[str], list[dict[str, Any]]] | None = None,
        action_requester: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
        progress_reader: Callable[[str], dict[str, Any] | None] | None = None,
        progress_writer: Callable[[str, dict[str, Any]], Any] | None = None,
    ) -> None:
        self.activity_reader = activity_reader
        self.revenue_reader = revenue_reader
        self.blocker_reader = blocker_reader or (lambda _client_id: [])
        self.action_requester = action_requester
        self.progress_reader = progress_reader or (lambda _client_id: None)
        self.progress_writer = progress_writer or (lambda _client_id, _record: None)

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
                "client_data_isolation": True,
            },
        }

    def deep_inspect(self, income_engine: Any, income_lifecycle: Any, client_id: str = TARGET_CLIENT_ID) -> dict[str, Any]:
        """Aggregate the existing income lifecycle without mutating it."""
        report = self.inspect(client_id)
        snapshot = income_engine.snapshot(client_id=client_id)
        lifecycle = income_lifecycle.summary(client_id=client_id)
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
        previous = self.progress_reader(client_id) or {}
        previous_revenue = float(previous.get("verified_revenue_jod", 0) or 0)
        delta = verified - previous_revenue
        if not previous:
            trend = "BASELINE"
        elif delta > 0:
            trend = "INCREASED"
        elif delta < 0:
            trend = "DECREASED"
        else:
            trend = "UNCHANGED"
        step = (
            "BASELINE_CAPTURED" if trend == "BASELINE"
            else "REVENUE_INCREASE_CONFIRMED" if trend == "INCREASED"
            else "REVENUE_UNCHANGED_REQUIRES_NEXT_STEP" if trend == "UNCHANGED"
            else "REVENUE_DECREASE_REQUIRES_RECOVERY_STEP"
        )
        next_action = (
            "CAPTURE_BASELINE_AND_START_ONE_REVENUE_PATH" if trend == "BASELINE"
            else "PROTECT_VERIFIED_PATH_AND_SCALE_ONE_STEP" if trend == "INCREASED"
            else "ADVANCE_ONE_EXISTING_OPPORTUNITY_AND_RECHECK_REVENUE" if trend == "UNCHANGED"
            else "RECOVER_ONE_REVENUE_PATH_BEFORE_ACCEPTING_NEW_WORK" if trend == "DECREASED"
        )
        escalation = (
            "NONE" if trend in {"BASELINE", "INCREASED"}
            else "ACTIVITY_ESCALATION" if trend == "UNCHANGED"
            else "REVENUE_RECOVERY_ESCALATION"
        )
        progress_record = {
            "target_client_id": client_id,
            "guardian_client_id": GUARDIAN_CLIENT_ID,
            "previous_verified_revenue_jod": previous_revenue,
            "current_verified_revenue_jod": verified,
            "delta_jod": delta,
            "trend": trend,
            "state": report.get("state"),
            "highest_priority": priority,
            "active_opportunities": len(active),
            "ready_to_apply": len(ready),
            "step": step,
            "next_action": next_action,
            "escalation": escalation,
            "action_constraint": "ONE_BOUNDED_ACTION_THROUGH_EXISTING_PRIMARY_PIPELINE",
            "dispatch_allowed": False,
        }
        self.progress_writer(client_id, progress_record)
        report["deep_audit"] = {
            "verified_revenue_jod": verified,
            "revenue_gap_exists": verified <= 0,
            "lifecycle_counts": dict(lifecycle.get("counts") or {}),
            "active_opportunities": len(active),
            "ready_to_apply": len(ready),
            "highest_priority": priority,
            "hard_gate": "PAYMENT_VERIFIED + payment_evidence",
            "evidence_chain": list(getattr(income_lifecycle, "ORDER", ())),
            "client_data_isolation": True,
            "revenue_trend": trend,
            "revenue_delta_jod": delta,
            "progress_step": progress_record["step"],
            "next_action": progress_record["next_action"],
            "escalation": progress_record["escalation"],
            "dispatch_allowed": False,
            "progress_history_saved": True,
        }
        return report

    @_guardian_advance_lock
    def advance_once(self, income_engine: Any, income_lifecycle: Any, client_id: str = TARGET_CLIENT_ID) -> dict[str, Any]:
        """Choose and request exactly one next step, then persist its outcome."""
        audit = self.deep_inspect(income_engine, income_lifecycle, client_id)
        deep = audit["deep_audit"]
        previous = self.progress_reader(client_id) or {}
        previous_action = str(previous.get("action_status") or "")
        previous_measurement = float(previous.get("current_verified_revenue_jod", 0) or 0)
        current_measurement = float(deep.get("verified_revenue_jod", 0) or 0)
        if previous_action == "REQUESTED" and current_measurement == previous_measurement:
            return {
                **audit,
                "status": "WAITING_FOR_RECHECK",
                "action_requested": False,
                "reason": "ONE_ACTION_ALREADY_REQUESTED_WITHOUT_NEW_REVENUE_MEASUREMENT",
                "verification_required": True,
            }
        if self.action_requester is None:
            return {**audit, "status": "ACTION_REQUESTER_NOT_REGISTERED", "action_requested": False}

        action = {
            "client_id": client_id,
            "guardian_client_id": GUARDIAN_CLIENT_ID,
            "objective": "MOVE_TOWARD_VERIFIED_REVENUE",
            "next_action": deep["next_action"],
            "trend": deep["revenue_trend"],
            "delta_jod": deep["revenue_delta_jod"],
            "escalation": deep["escalation"],
            "constraint": "ONE_BOUNDED_ACTION_THROUGH_EXISTING_PRIMARY_PIPELINE",
            "verified_revenue_only": True,
        }
        result = self.action_requester(client_id, action)
        outcome = result if isinstance(result, dict) else {"result": result}
        record = {
            **(self.progress_reader(client_id) or {}),
            "target_client_id": client_id,
            "guardian_client_id": GUARDIAN_CLIENT_ID,
            "action_requested": deep["next_action"],
            "action_outcome": outcome,
            "action_status": "REQUESTED",
            "dispatch_allowed": False,
        }
        self.progress_writer(client_id, record)
        return {
            **audit,
            "status": "NEXT_STEP_REQUESTED",
            "action_requested": True,
            "action": action,
            "action_result": outcome,
            "verification_required": True,
        }

    def first_revenue_mission(self, income_engine: Any, income_lifecycle: Any, client_id: str = TARGET_CLIENT_ID) -> dict[str, Any]:
        """Create a bounded first-revenue mission; never fabricates a buyer, action, or payment."""
        audit = self.deep_inspect(income_engine, income_lifecycle, client_id)
        deep = audit["deep_audit"]
        revenue = float(deep.get("verified_revenue_jod", 0) or 0)
        if revenue >= 10:
            return {**audit, "status": "FIRST_REVENUE_TARGET_REACHED", "target_jod": 10.0}

        previous = self.progress_reader(client_id) or {}
        if previous.get("first_revenue_mission_status") == "PENDING_EXTERNAL_EVIDENCE":
            return {
                **audit,
                "status": "FIRST_REVENUE_MISSION_PENDING",
                "target_jod": 10.0,
                "verification_required": True,
            }

        mission = {
            "client_id": client_id,
            "guardian_client_id": GUARDIAN_CLIENT_ID,
            "target_jod": 10.0,
            "objective": "ACHIEVE_FIRST_VERIFIED_REVENUE",
            "opportunity_limit": 1,
            "external_action_limit": 1,
            "payment_verification_required": True,
            "constraint": "ONE_OPPORTUNITY_ONE_EXTERNAL_ACTION",
            "no_fabricated_buyer_or_payment": True,
        }
        record = {
            **previous,
            "target_client_id": client_id,
            "guardian_client_id": GUARDIAN_CLIENT_ID,
            "first_revenue_mission_status": "PENDING_EXTERNAL_EVIDENCE",
            "first_revenue_target_jod": 10.0,
            "first_revenue_mission": mission,
            "dispatch_allowed": False,
        }
        self.progress_writer(client_id, record)
        return {
            **audit,
            "status": "FIRST_REVENUE_MISSION_CREATED",
            "mission": mission,
            "verification_required": True,
        }

    def reconcile_once(self, income_engine: Any, income_lifecycle: Any, client_id: str = TARGET_CLIENT_ID) -> dict[str, Any]:
        """Reconcile the last requested action against a fresh revenue measurement."""
        current = self.deep_inspect(income_engine, income_lifecycle, client_id)
        deep = current["deep_audit"]
        previous = self.progress_reader(client_id) or {}
        action_status = str(previous.get("action_status") or "")
        if action_status != "REQUESTED":
            return {**current, "status": "NO_PENDING_ACTION", "reconciliation": "NONE"}

        before = float(previous.get("previous_verified_revenue_jod", previous.get("current_verified_revenue_jod", 0)) or 0)
        after = float(deep.get("verified_revenue_jod", 0) or 0)
        if after > before:
            reconciliation = "ACTION_EFFECTIVE"
        elif after < before:
            reconciliation = "ACTION_REQUIRES_RECOVERY"
        else:
            reconciliation = "ACTION_NO_PROGRESS_NEEDS_EVIDENCE"

        record = {
            **previous,
            "target_client_id": client_id,
            "guardian_client_id": GUARDIAN_CLIENT_ID,
            "action_status": reconciliation,
            "reconciled_verified_revenue_jod": after,
            "reconciliation_required": False,
            "dispatch_allowed": False,
        }
        self.progress_writer(client_id, record)
        return {
            **current,
            "status": "ACTION_RECONCILED",
            "reconciliation": reconciliation,
            "before_verified_revenue_jod": before,
            "after_verified_revenue_jod": after,
            "next_action_allowed": reconciliation != "ACTION_NO_PROGRESS_NEEDS_EVIDENCE",
        }

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
