"""Commercial incident containment.

A reconciliation failure creates a containment state. It never silently
rewrites financial history.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ContainmentIncident:
    incident_id: str
    order_id: str
    reason: str
    detected_at: str
    active: bool = True


class CommercialContainmentGate:
    def __init__(self) -> None:
        self._incidents: dict[str, ContainmentIncident] = {}

    def contain(self, incident_id: str, order_id: str, reason: str) -> ContainmentIncident:
        if incident_id in self._incidents:
            raise ValueError(f"DUPLICATE_INCIDENT:{incident_id}")
        incident = ContainmentIncident(
            incident_id=incident_id,
            order_id=order_id,
            reason=reason,
            detected_at=datetime.now(timezone.utc).isoformat(),
        )
        self._incidents[incident_id] = incident
        return incident

    def is_contained(self, order_id: str) -> bool:
        return any(i.order_id == order_id and i.active for i in self._incidents.values())

    def assert_clear(self, order_id: str) -> None:
        if self.is_contained(order_id):
            raise RuntimeError(f"COMMERCIAL_ORDER_CONTAINED:{order_id}")

    def release(self, incident_id: str) -> None:
        incident = self._incidents.get(incident_id)
        if incident is None:
            raise KeyError(f"UNKNOWN_INCIDENT:{incident_id}")
        self._incidents[incident_id] = ContainmentIncident(
            incident_id=incident.incident_id,
            order_id=incident.order_id,
            reason=incident.reason,
            detected_at=incident.detected_at,
            active=False,
        )

    def active_incidents(self, order_id: str) -> list[ContainmentIncident]:
        return [
            i for i in self._incidents.values()
            if i.order_id == order_id and i.active
        ]
