"""Human approval gate for high-risk or irreversible actions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ApprovalRequest:
    request_id: str
    order_id: str
    action: str
    reason: str
    created_at: str
    approved: bool = False


class HumanApprovalGate:
    def __init__(self) -> None:
        self._requests: dict[str, ApprovalRequest] = {}

    def request(self, request_id: str, order_id: str, action: str, reason: str) -> ApprovalRequest:
        if request_id in self._requests:
            raise ValueError(f"DUPLICATE_APPROVAL_REQUEST:{request_id}")
        request = ApprovalRequest(
            request_id=request_id,
            order_id=order_id,
            action=action,
            reason=reason,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._requests[request_id] = request
        return request

    def approve(self, request_id: str) -> ApprovalRequest:
        current = self._requests.get(request_id)
        if current is None:
            raise KeyError(f"UNKNOWN_APPROVAL_REQUEST:{request_id}")
        approved = ApprovalRequest(
            request_id=current.request_id,
            order_id=current.order_id,
            action=current.action,
            reason=current.reason,
            created_at=current.created_at,
            approved=True,
        )
        self._requests[request_id] = approved
        return approved

    def is_approved(self, request_id: str) -> bool:
        request = self._requests.get(request_id)
        return bool(request and request.approved)

    def assert_approved(self, request_id: str) -> None:
        if not self.is_approved(request_id):
            raise RuntimeError(f"HUMAN_APPROVAL_REQUIRED:{request_id}")
