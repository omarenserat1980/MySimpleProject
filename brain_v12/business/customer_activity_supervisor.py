"""Cross-customer activity reporting and bounded continuation supervisor.

This layer is read/repair orchestration only. It does not expose one customer's
private data to another customer and never declares completion without evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Callable


TERMINAL = {"COMPLETED", "CLOSED", "CANCELLED", "VERIFIED_COMPLETED"}
ACTIVE = {"NEW", "READY_FOR_REVIEW", "APPROVED", "DISCOVERED", "PENDING", "RUNNING", "RETRYING", "QUEUED", "IN_PROGRESS", "TRIAL_REQUESTED"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _evidence_ref(payload: Any) -> str:
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    ).hexdigest()
    return f"evidence://customer-activity/{digest}"


@dataclass
class ActivityResult:
    customer_id: str
    activity_id: str
    status: str
    action: str
    evidence_ref: str | None = None
    error: str | None = None


class CustomerActivitySupervisor:
    """Report customer activities and continue unfinished work safely.

    The supervisor accepts an injected repair/resume callback so the actual
    executor remains behind Brain's existing permission and execution gates.
    """

    def __init__(self, state_root: str | Path, repair_resume: Callable[[dict], dict] | None = None):
        self.root = Path(state_root)
        self.customer_root = self.root / "customer_requests"
        self.client_root = self.root / "client_accounts"
        self.repair_resume = repair_resume

    @staticmethod
    def _state(record: dict) -> str:
        return str(record.get("status") or record.get("lifecycle_state") or "UNKNOWN").upper()

    def _customer_records(self) -> list[dict]:
        items = []
        if not self.customer_root.is_dir():
            return items
        for path in sorted(self.customer_root.glob("*.json")):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
                record["_source"] = "customer_request"
                items.append(record)
            except (OSError, json.JSONDecodeError):
                continue
        return items

    def _client_accounts(self) -> list[dict]:
        items = []
        if not self.client_root.is_dir():
            return items
        for path in sorted(self.client_root.glob("*.json")):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
                record["_source"] = "client_account"
                items.append(record)
            except (OSError, json.JSONDecodeError):
                continue
        return items

    def report(self, include_completed: bool = True) -> dict:
        customers = []
        for record in self._customer_records():
            activities = []
            activities.append({
                "activity_id": record.get("request_id"),
                "type": "CUSTOMER_REQUEST",
                "service": record.get("service"),
                "need": record.get("need"),
                "status": self._state(record),
                "completed": self._state(record) in TERMINAL,
                "source": record.get("_source"),
            })
            for action in record.get("external_actions", []):
                activities.append({
                    "activity_id": action.get("message_id") or action.get("action"),
                    "type": action.get("action", "EXTERNAL_ACTION"),
                    "status": str(action.get("status", "UNKNOWN")).upper(),
                    "completed": str(action.get("status", "")).upper() in TERMINAL,
                    "source": "customer_request",
                })
            customers.append({
                "customer_id": record.get("request_id"),
                "display_name": record.get("display_name"),
                "customer_type": record.get("customer_type"),
                "activities": [a for a in activities if include_completed or not a["completed"]],
            })

        for account in self._client_accounts():
            customer_id = account.get("client_id")
            activities = []
            for order in account.get("orders", []):
                state = str(order.get("state", "UNKNOWN")).upper()
                activities.append({
                    "activity_id": order.get("order_id"),
                    "type": "CLIENT_ORDER",
                    "service": order.get("service"),
                    "need": order.get("need"),
                    "status": state,
                    "completed": state in TERMINAL,
                    "source": "client_account",
                })
            if activities or customer_id:
                customers.append({
                    "customer_id": customer_id,
                    "display_name": account.get("display_name"),
                    "customer_type": "CLIENT_ACCOUNT",
                    "activities": [a for a in activities if include_completed or not a["completed"]],
                })

        total = sum(len(c["activities"]) for c in customers)
        unfinished = sum(
            1 for c in customers for a in c["activities"] if not a["completed"]
        )
        return {
            "ok": True,
            "generated_at": _now(),
            "customer_count": len(customers),
            "activity_count": total,
            "unfinished_activity_count": unfinished,
            "customers": customers,
            "policy": {
                "cross_customer_report": "AUTHORIZED_OPERATOR_ONLY",
                "completion_requires_evidence": True,
                "unfinished_action": "INSPECT_DIAGNOSE_REPAIR_RESUME_VERIFY",
            },
        }

    def continue_unfinished(self, customer_id: str | None = None, limit: int = 50) -> dict:
        report = self.report(include_completed=False)
        targets = []
        for customer in report["customers"]:
            if customer_id and customer["customer_id"] != customer_id:
                continue
            for activity in customer["activities"]:
                if not activity["completed"]:
                    targets.append((customer, activity))
        targets = targets[:max(1, min(int(limit), 200))]

        results = []
        for customer, activity in targets:
            payload = {
                "customer_id": customer["customer_id"],
                "activity": activity,
                "inspection": {
                    "status": activity["status"],
                    "unfinished": True,
                    "checked_at": _now(),
                },
            }
            if self.repair_resume is None:
                results.append(ActivityResult(
                    customer_id=customer["customer_id"],
                    activity_id=str(activity["activity_id"]),
                    status="WAITING_EXECUTOR",
                    action="INSPECTED_ONLY",
                ).__dict__)
                continue
            try:
                execution = self.repair_resume(payload)
            except Exception as exc:
                results.append(ActivityResult(
                    customer_id=customer["customer_id"],
                    activity_id=str(activity["activity_id"]),
                    status="REPAIR_FAILED",
                    action="REPAIR_RESUME",
                    error=f"{type(exc).__name__}:{exc}",
                ).__dict__)
                continue

            verification = execution.get("verification") if isinstance(execution, dict) else None
            verified = (
                isinstance(verification, dict)
                and verification.get("passed") is True
                and str(verification.get("criterion", "")).strip()
                and execution.get("completed") is True
            )
            if verified:
                evidence = execution.get("evidence") or execution
                results.append(ActivityResult(
                    customer_id=customer["customer_id"],
                    activity_id=str(activity["activity_id"]),
                    status="VERIFIED_COMPLETED",
                    action="INSPECT_DIAGNOSE_REPAIR_RESUME_VERIFY",
                    evidence_ref=_evidence_ref(evidence),
                ).__dict__)
            else:
                results.append(ActivityResult(
                    customer_id=customer["customer_id"],
                    activity_id=str(activity["activity_id"]),
                    status="NOT_COMPLETED",
                    action="INSPECT_DIAGNOSE_REPAIR_RESUME_VERIFY",
                    error="OBJECTIVE_VERIFICATION_REQUIRED",
                ).__dict__)

        return {
            "ok": all(r["status"] == "VERIFIED_COMPLETED" for r in results) if results else True,
            "status": "COMPLETED" if results and all(r["status"] == "VERIFIED_COMPLETED" for r in results) else ("NO_UNFINISHED_ACTIVITIES" if not results else "CONTINUATION_INCOMPLETE"),
            "checked": len(targets),
            "results": results,
            "report_after": self.report(include_completed=False),
        }
