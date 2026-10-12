"""Auditable human approval records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .decision_audit import DecisionAuditLog
from .human_approval import HumanApprovalGate


@dataclass(frozen=True)
class ApprovalAuditResult:
    request_id: str
    approved: bool
    decision_id: str


class AuditedHumanApprovalGate:
    def __init__(
        self,
        approvals: HumanApprovalGate,
        decisions: DecisionAuditLog,
    ) -> None:
        self.approvals = approvals
        self.decisions = decisions

    def approve(
        self,
        request_id: str,
        decision_id: str,
    ) -> ApprovalAuditResult:
        request = self.approvals.approve(request_id)
        self.decisions.record(
            decision_id,
            request.order_id,
            request.action,
            True,
            "HUMAN_APPROVAL_GRANTED",
            metadata={
                "approval_request_id": request_id,
                "approval_reason": request.reason,
                "approved_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        return ApprovalAuditResult(request_id, True, decision_id)
