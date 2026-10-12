"""Time-bound, single-use human approvals."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone

from .decision_audit import DecisionAuditLog
from .human_approval import HumanApprovalGate


@dataclass(frozen=True)
class ApprovalRecord:
    request_id: str
    order_id: str
    action: str
    reason: str
    created_at: str
    expires_at: str
    approved: bool = False
    consumed: bool = False


class SecureHumanApprovalGate(HumanApprovalGate):
    def __init__(self, ttl_seconds: int = 900) -> None:
        super().__init__()
        if ttl_seconds <= 0:
            raise ValueError("TTL_MUST_BE_POSITIVE")
        self.ttl_seconds = ttl_seconds
        self._secure: dict[str, ApprovalRecord] = {}

    def request(self, request_id: str, order_id: str, action: str, reason: str) -> ApprovalRecord:
        if request_id in self._secure:
            raise ValueError(f"DUPLICATE_APPROVAL_REQUEST:{request_id}")
        now = datetime.now(timezone.utc)
        record = ApprovalRecord(
            request_id=request_id,
            order_id=order_id,
            action=action,
            reason=reason,
            created_at=now.isoformat(),
            expires_at=(now + timedelta(seconds=self.ttl_seconds)).isoformat(),
        )
        self._secure[request_id] = record
        return record

    def approve(self, request_id: str) -> ApprovalRecord:
        record = self._get_valid(request_id)
        if record.consumed:
            raise RuntimeError(f"APPROVAL_ALREADY_CONSUMED:{request_id}")
        updated = replace(record, approved=True)
        self._secure[request_id] = updated
        return updated

    def consume(self, request_id: str) -> ApprovalRecord:
        record = self._get_valid(request_id)
        if not record.approved:
            raise RuntimeError(f"HUMAN_APPROVAL_REQUIRED:{request_id}")
        if record.consumed:
            raise RuntimeError(f"APPROVAL_ALREADY_CONSUMED:{request_id}")
        updated = replace(record, consumed=True)
        self._secure[request_id] = updated
        return updated

    def _get_valid(self, request_id: str) -> ApprovalRecord:
        record = self._secure.get(request_id)
        if record is None:
            raise KeyError(f"UNKNOWN_APPROVAL_REQUEST:{request_id}")
        if datetime.now(timezone.utc) >= datetime.fromisoformat(record.expires_at):
            raise RuntimeError(f"APPROVAL_EXPIRED:{request_id}")
        return record


class AuditedSecureApprovalService:
    def __init__(self, approvals: SecureHumanApprovalGate, decisions: DecisionAuditLog) -> None:
        self.approvals = approvals
        self.decisions = decisions

    def consume_for_action(self, request_id: str, decision_id: str) -> ApprovalRecord:
        record = self.approvals.consume(request_id)
        self.decisions.record(
            decision_id,
            record.order_id,
            record.action,
            True,
            "HUMAN_APPROVAL_CONSUMED",
            metadata={"approval_request_id": request_id},
        )
        return record
