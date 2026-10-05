from __future__ import annotations

import time
from dataclasses import dataclass

from .audit_chain import AuditChain
from .permissions import ActionRisk
from .persistent_state import SQLiteStateStore


@dataclass(frozen=True)
class ApprovalDecision:
    approved: bool
    task_id: str
    action: str
    risk: ActionRisk
    reason: str


class AuthorityApprovalLedger:
    """Durable, explicit approval ledger for actions requiring higher authority."""

    def __init__(self, state: SQLiteStateStore, audit: AuditChain) -> None:
        self.state = state
        self.audit = audit

    def approve(self, task_id: str, action: str, risk: ActionRisk, approver: str) -> ApprovalDecision:
        if not task_id or not action or not approver:
            return ApprovalDecision(False, task_id, action, risk, "task_id, action and approver are required")
        if risk is not ActionRisk.IRREVERSIBLE:
            return ApprovalDecision(False, task_id, action, risk, "explicit authority approval is only required for irreversible actions")
        record = {
            "task_id": task_id,
            "action": action,
            "risk": risk.value,
            "approver": approver,
            "approved_at": time.time(),
            "consumed": False,
        }
        self.state.set(f"authority:approval:{task_id}", record)
        self.audit.record("authority.approved", {
            "task_id": task_id, "action": action, "risk": risk.value, "approver": approver,
        })
        return ApprovalDecision(True, task_id, action, risk, "explicit approval recorded")

    def check(self, task_id: str, action: str, risk: ActionRisk) -> ApprovalDecision:
        record = self.state.get(f"authority:approval:{task_id}")
        if not record:
            return ApprovalDecision(False, task_id, action, risk, "explicit irreversible approval is missing")
        if record.get("consumed") is True:
            return ApprovalDecision(False, task_id, action, risk, "explicit approval has already been consumed")
        if record.get("action") != action or record.get("risk") != risk.value:
            return ApprovalDecision(False, task_id, action, risk, "approval does not match requested action or risk")
        return ApprovalDecision(True, task_id, action, risk, "explicit approval valid")

    def consume(self, task_id: str, action: str, risk: ActionRisk) -> ApprovalDecision:
        decision = self.check(task_id, action, risk)
        if not decision.approved:
            return decision
        record = self.state.get(f"authority:approval:{task_id}")
        self.state.set(f"authority:approval:{task_id}", {**record, "consumed": True, "consumed_at": time.time()})
        self.audit.record("authority.consumed", {"task_id": task_id, "action": action, "risk": risk.value})
        return ApprovalDecision(True, task_id, action, risk, "explicit approval consumed")


__all__ = ["ApprovalDecision", "AuthorityApprovalLedger"]
