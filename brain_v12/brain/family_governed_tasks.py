"""Enforce family governance before persistent tasks are queued or executed.

This integration accepts approval metadata only from a trusted caller. The
agent deliberately does not expose an API for self-asserting verified identity.
"""
from __future__ import annotations

from typing import Any
import hashlib
import json

from .family_policy_audit import FamilyPolicyAudit
from .family_approval_verifier import DenyAllFamilyApprovalVerifier, FamilyApprovalVerifier
from .family_governance import FamilyApproval, FamilyGovernance
from .initial_software_node import ALLOWED_TASKS

TASK_POLICY = {
    "health_check": ("health_check", "low", False),
    "write_text": ("workspace_change", "medium", False),
    "read_text": ("read_private_data", "high", False),
    "run_brainvm": ("run_brainvm", "medium", False),
    "network_self_test": ("network_self_test", "low", False),
}

class FamilyGovernedTaskService:
    """Policy-aware facade for enqueuing work and recording policy decisions."""

    def __init__(self, queue: Any, governance: FamilyGovernance | None = None,
                 approval_verifier: FamilyApprovalVerifier | None = None):
        self.queue = queue
        self.governance = governance or FamilyGovernance()
        self.approval_verifier = approval_verifier or DenyAllFamilyApprovalVerifier()
        self.audit = FamilyPolicyAudit(queue.database_path)
        self.audit_log: list[dict[str, Any]] = []

    def enqueue(
        self,
        task: dict[str, Any],
        *,
        idempotency_key: str | None = None,
        approval: FamilyApproval | None = None,
    ) -> dict[str, Any]:
        if not isinstance(task, dict):
            return self._deny("INVALID_TASK", "")
        kind = task.get("type")
        if kind not in ALLOWED_TASKS or kind not in TASK_POLICY:
            return self._deny("TASK_TYPE_NOT_ALLOWED", str(kind or ""))
        action, risk, irreversible = TASK_POLICY[kind]
        fingerprint = hashlib.sha256(
            json.dumps(task, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        ).hexdigest()
        verified_approval = None
        if approval is not None:
            try:
                if self.approval_verifier.verify(
                    approval=approval, action=action, task_fingerprint=fingerprint
                ):
                    verified_approval = approval
            except Exception:
                # Verifier errors fail closed and never unlock a sensitive task.
                verified_approval = None
        decision = self.governance.evaluate(
            action,
            risk=risk,
            irreversible=irreversible,
            approval=verified_approval,
        )
        event = {
            "event": "FAMILY_POLICY_DECISION",
            "task_type": kind,
            "decision": decision,
            "approval_verifier": "TRUSTED_VERIFIER_ACCEPTED" if verified_approval else
                                 ("DENY_ALL_DEFAULT" if approval is not None else "NO_APPROVAL_SUPPLIED"),
        }
        self._record(event)
        if not decision["ok"]:
            return {
                "ok": False,
                "status": decision["status"],
                "task_type": kind,
                "family_policy": decision,
                "queued": False,
            }
        if decision.get("approval_required"):
            if verified_approval is None or not self.audit.consume_approval(
                verified_approval.consent_reference, action, fingerprint
            ):
                replay = self.governance.evaluate(action, risk="high")
                event = {"event": "FAMILY_APPROVAL_REPLAY_OR_INVALID", "task_type": kind,
                         "action": action, "task_fingerprint": fingerprint}
                self._record(event)
                return {"ok": False, "status": "FAMILY_APPROVAL_REPLAY_BLOCKED",
                        "task_type": kind, "family_policy": replay, "queued": False}
        queued = self.queue.enqueue(task, idempotency_key=idempotency_key)
        queued["family_policy"] = decision
        queued["queued"] = True
        return queued

    def _record(self, event: dict[str, Any]) -> None:
        # Fail closed if the durable policy audit cannot be written.
        persisted = self.audit.append(event)
        event["audit"] = persisted
        self.audit_log.append(event)

    def audit_status(self) -> dict[str, Any]:
        return self.audit.verify()

    def _deny(self, status: str, task_type: str) -> dict[str, Any]:
        decision = self.governance.evaluate("invalid_task", risk="high")
        self._record({"event": "FAMILY_POLICY_DENIAL", "task_type": task_type, "status": status})
        return {
            "ok": False,
            "status": status,
            "task_type": task_type,
            "family_policy": decision,
            "queued": False,
        }
