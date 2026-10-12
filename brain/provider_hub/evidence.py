"""Immutable-style evidence records for BRAIN commercial gates."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    evidence_type: str
    order_id: str
    source: str
    reference: str
    observed_at: str
    payload: dict[str, Any]

    @classmethod
    def create(cls, evidence_id: str, evidence_type: str, order_id: str, source: str, reference: str, payload: dict[str, Any]) -> "Evidence":
        return cls(evidence_id, evidence_type, order_id, source, reference, datetime.now(timezone.utc).isoformat(), payload)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class CommercialEvidenceGate:
    def __init__(self) -> None:
        self._records: dict[str, Evidence] = {}

    def add(self, evidence: Evidence) -> None:
        if evidence.evidence_id in self._records:
            raise ValueError(f"DUPLICATE_EVIDENCE:{evidence.evidence_id}")
        self._records[evidence.evidence_id] = evidence

    def for_order(self, order_id: str, evidence_type: str | None = None) -> list[Evidence]:
        rows = [e for e in self._records.values() if e.order_id == order_id]
        return [e for e in rows if evidence_type is None or e.evidence_type == evidence_type]

    def can_mark_payment_verified(
        self,
        evidence_or_order: list[Evidence] | str,
        order_id: str | None = None,
    ) -> bool:
        # Supports both the original order-id API and the evidence-list API
        # used by adapter bridges.
        if isinstance(evidence_or_order, str):
            target = evidence_or_order
        else:
            target = order_id
            if target is None:
                raise ValueError("ORDER_ID_REQUIRED")
            for evidence in evidence_or_order:
                if evidence.order_id != target or evidence.evidence_type != "PAYMENT_VERIFICATION":
                    return False
                self.add(evidence)
        return bool(self.for_order(target, "PAYMENT_VERIFICATION"))

    def can_mark_revenue_realized(self, order_id: str) -> bool:
        return self.can_mark_payment_verified(order_id) and bool(self.for_order(order_id, "REVENUE_CONFIRMATION"))

    def can_mark_delivery_verified(self, order_id: str) -> bool:
        return bool(self.for_order(order_id, "DELIVERY_VERIFICATION"))
