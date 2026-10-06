"""Bounded revenue guardian for an active Brain client.

The guardian observes one target client, distinguishes verified revenue from
mere activity/opportunities, identifies blockers, and can request one bounded
next action through the existing primary pipeline.

It never fabricates revenue, never treats opportunities as payments, and never
creates parallel workflows.
"""
from __future__ import annotations

from threading import Lock

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
            else "RECOVER_ONE_REVENUE_PATH_BEFORE_ACCEPTING_NEW_WORK"
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

    def promote_successful_projects_once(self, income_engine: Any, income_lifecycle: Any, client_id: str = TARGET_CLIENT_ID) -> dict[str, Any]:
        """Find completed client projects, count them, and request one bounded social-marketing action."""
        snapshot = income_engine.snapshot(client_id=client_id)
        rows = list(snapshot.get("opportunities") or [])
        successful = [
            r for r in rows
            if str(r.get("status") or "") in ("COMPLETED", "PAYMENT_VERIFIED")
            and str((r.get("data") or {}).get("delivery_evidence") or "").strip()
        ]
        previous = self.progress_reader(client_id) or {}
        marketed = set(previous.get("marketed_successful_project_ids") or [])
        candidate = next((r for r in successful if str(r.get("opportunity_id")) not in marketed), None)
        revenue = float(snapshot.get("verified_revenue_jod", 0) or 0)
        record = {
            **previous,
            "successful_projects_count": len({str(r.get("opportunity_id")) for r in successful}),
            "successful_projects_revenue_jod": revenue,
            "successful_projects_checked": True,
        }
        if not candidate:
            record["marketing_status"] = "NO_NEW_SUCCESSFUL_PROJECT"
            self.progress_writer(client_id, record)
            return {
                "status": "SUCCESSFUL_PROJECTS_CHECKED",
                "successful_projects_count": record["successful_projects_count"],
                "verified_revenue_jod": revenue,
                "marketing_requested": False,
            }

        project_id = str(candidate.get("opportunity_id"))
        title = str((candidate.get("data") or {}).get("title") or candidate.get("title") or project_id)
        project_data = dict(candidate.get("data") or {})
        project_revenue_before = float(candidate.get("verified_amount_jod") or project_data.get("verified_amount_jod") or 0)
        marketing_baselines = dict(previous.get("marketing_revenue_baselines") or {})
        marketing_baselines[project_id] = project_revenue_before
        media_path = str(project_data.get("media_path") or "").strip()
        marketing_asset_ready = bool(media_path)
        action = {
            "client_id": client_id,
            "guardian_client_id": GUARDIAN_CLIENT_ID,
            "objective": "MARKET_SUCCESSFUL_PROJECT_ON_SOCIAL_MEDIA",
            "project_id": project_id,
            "project_title": title,
            "channel": "SOCIAL_MEDIA",
            "marketing_asset_ready": marketing_asset_ready,
            "media_path": media_path,
            "execution_gate": "REQUIRE_PUBLISH_PROVIDER_AND_VALID_MEDIA_BEFORE_EXTERNAL_PUBLISH",
            "constraint": "ONE_SUCCESSFUL_PROJECT_ONE_BOUNDED_MARKETING_ACTION",
            "revenue_tracking_required": True,
            "payment_verification_required": True,
            "no_fabricated_results": True,
        }
        result = self.action_requester(client_id, action) if self.action_requester else {
            "accepted": False, "status": "ACTION_REQUESTER_NOT_REGISTERED"
        }
        outcome = result if isinstance(result, dict) else {"result": result}
        if bool(outcome.get("accepted")):
            marketed.add(project_id)
        record.update({
            "marketed_successful_project_ids": sorted(marketed),
            "marketing_status": "PENDING_EXTERNAL_EVIDENCE",
            "last_marketed_project_id": project_id,
            "last_marketing_action": action,
            "last_marketing_outcome": outcome,
            "marketing_revenue_baselines": marketing_baselines,
            "last_marketing_revenue_before_jod": project_revenue_before,
        })
        self.progress_writer(client_id, record)
        if hasattr(self.progress_writer, "__self__") and hasattr(self.progress_writer.__self__, "save_revenue_project_marketing_result"):
            self.progress_writer.__self__.save_revenue_project_marketing_result(client_id, {
                "project_id": project_id,
                "project_title": title,
                "marketing_status": record["marketing_status"],
                "marketing_result": outcome,
                "revenue_before_jod": project_revenue_before,
                "verified_revenue_jod_at_request": revenue,
            })
        return {
            "status": "SUCCESSFUL_PROJECT_MARKETING_REQUESTED",
            "successful_projects_count": record["successful_projects_count"],
            "project_id": project_id,
            "project_title": title,
            "marketing_requested": True,
            "marketing_result": outcome,
            "verified_revenue_jod": revenue,
            "revenue_tracking_required": True,
            "revenue_baseline_jod": project_revenue_before,
            "revenue_attribution_scope": "PROJECT_ONLY_WHEN_PROJECT_PAYMENT_EVIDENCE_IS_CLIENT_SCOPED",
        }

    def reconcile_marketing_once(self, income_engine: Any, client_id: str = TARGET_CLIENT_ID) -> dict[str, Any]:
        """Measure a marketed project's revenue delta without over-attributing unrelated revenue."""
        previous = self.progress_reader(client_id) or {}
        project_id = str(previous.get("last_marketed_project_id") or "")
        if not project_id:
            return {"status": "NO_MARKETED_PROJECT_TO_RECONCILE"}

        snapshot = income_engine.snapshot(client_id=client_id)
        rows = list(snapshot.get("opportunities") or [])
        row = next((r for r in rows if str(r.get("opportunity_id")) == project_id), None)
        if not row:
            return {"status": "PROJECT_NOT_FOUND", "project_id": project_id}

        data = dict(row.get("data") or {})
        after = float(row.get("verified_amount_jod") or data.get("verified_amount_jod") or 0)
        before = float((previous.get("marketing_revenue_baselines") or {}).get(project_id, 0) or 0)
        delta = after - before
        evidence = str(data.get("payment_evidence") or "").strip()

        if delta > 0 and evidence:
            attribution = "PROJECT_REVENUE_INCREASE_WITH_PAYMENT_EVIDENCE"
        elif delta == 0:
            attribution = "NO_PROJECT_REVENUE_CHANGE"
        else:
            attribution = "UNATTRIBUTED_OR_INSUFFICIENT_PROJECT_EVIDENCE"

        result = {
            "status": "MARKETING_RECONCILED",
            "project_id": project_id,
            "revenue_before_jod": before,
            "revenue_after_jod": after,
            "revenue_delta_jod": delta,
            "payment_evidence_present": bool(evidence),
            "attribution": attribution,
            "verified_revenue_jod": float(snapshot.get("verified_revenue_jod", 0) or 0),
            "successful_projects_count": sum(
                1 for r in rows
                if str(r.get("status") or "") in ("COMPLETED", "PAYMENT_VERIFIED")
                and str((r.get("data") or {}).get("delivery_evidence") or "").strip()
            ),
        }
        self.progress_writer(client_id, {
            **previous,
            "last_marketing_reconciliation": result,
            "last_marketing_attribution": attribution,
        })
        if hasattr(self.progress_writer, "__self__") and hasattr(self.progress_writer.__self__, "save_revenue_project_marketing_result"):
            self.progress_writer.__self__.save_revenue_project_marketing_result(client_id, result)
        return result

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
