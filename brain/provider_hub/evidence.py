"""Immutable-style evidence records for BRAIN commercial gates.

This module does not perform payments. It records verifiable evidence supplied by
trusted adapters and exposes deterministic gates for payment, revenue and delivery.
"""

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
    def create(
        cls,
        evidence_id: str,
        evidence_type: str,
        order_id: str,
        source: str,
        reference: str,
        payload: dict[str, Any],
    ) -> "Evidence":
        return cls(
            evidence_id=evidence_id,
            evidence_type=evidence_type,
            order_id=order_id,
            source=source,
            reference=reference,
            observed_at=datetime.now(timezone.utc).isoformat(),
            payload=payload,
        )

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
        if evidence_type:
            rows = [e for e in rows if e.evidence_type == evidence_type]
        return rows

    def can_mark_payment_verified(self, order_id: str) -> bool:
        return bool(self.for_order(order_id, "PAYMENT_VERIFICATION"))

    def can_mark_revenue_realized(self, order_id: str) -> bool:
        return self.can_mark_payment_verified(order_id) and bool(
            self.for_order(order_id, "REVENUE_CONFIRMATION")
        )

    def can_mark_delivery_verified(self, order_id: str) -> bool:
        return bool(self.for_order(order_id, "DELIVERY_VERIFICATION"))
