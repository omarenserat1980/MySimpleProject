"""Auditable decisions for the unified commercial action gate."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class ActionDecisionEvent:
    decision_id: str
    order_id: str
    action: str
    allowed: bool
    reason: str
    decided_at: str
    evidence_refs: tuple[str, ...]
    metadata: dict[str, Any]


class DecisionAuditLog:
    def __init__(self) -> None:
        self._events: list[ActionDecisionEvent] = []
        self._ids: set[str] = set()

    def record(
        self,
        decision_id: str,
        order_id: str,
        action: str,
        allowed: bool,
        reason: str,
        evidence_refs: tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
    ) -> ActionDecisionEvent:
        if decision_id in self._ids:
            raise ValueError(f"DUPLICATE_DECISION:{decision_id}")
        event = ActionDecisionEvent(
            decision_id=decision_id,
            order_id=order_id,
            action=action,
            allowed=allowed,
            reason=reason,
            decided_at=datetime.now(timezone.utc).isoformat(),
            evidence_refs=evidence_refs,
            metadata=metadata or {},
        )
        self._ids.add(decision_id)
        self._events.append(event)
        return event

    def for_order(self, order_id: str) -> list[ActionDecisionEvent]:
        return [e for e in self._events if e.order_id == order_id]

    def export(self) -> list[dict[str, Any]]:
        return [asdict(e) for e in self._events]
