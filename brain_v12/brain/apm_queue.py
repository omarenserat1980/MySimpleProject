"""Durable, dependency-aware APM work queue."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class QueueUnit:
    unit_id: str
    depends_on: tuple[str, ...] = ()
    priority: int = 100
    state: str = "QUEUED"
    attempt: int = 0
    worker_id: str | None = None


class APMQueue:
    def __init__(self, units: Iterable[QueueUnit] = ()):
        self.units: dict[str, QueueUnit] = {}
        for unit in units:
            self.add(unit)

    def add(self, unit: QueueUnit) -> None:
        if unit.unit_id in self.units:
            raise ValueError(f"duplicate unit: {unit.unit_id}")
        self.units[unit.unit_id] = unit

    def ready(self) -> list[QueueUnit]:
        out = []
        for unit in self.units.values():
            if unit.state != "QUEUED":
                continue
            if all(
                dep in self.units and self.units[dep].state == "VERIFIED_COMPLETED"
                for dep in unit.depends_on
            ):
                out.append(unit)
        return sorted(out, key=lambda x: (x.priority, x.unit_id))

    def claim(self, worker_id: str) -> QueueUnit | None:
        candidates = self.ready()
        if not candidates:
            return None
        unit = candidates[0]
        unit.state = "CLAIMED"
        unit.worker_id = worker_id
        unit.attempt += 1
        return unit

    def complete(self, unit_id: str) -> None:
        unit = self.units[unit_id]
        if unit.state != "CLAIMED":
            raise ValueError("only claimed units can complete")
        unit.state = "VERIFIED_COMPLETED"

    def requeue_expired(self, unit_id: str) -> None:
        unit = self.units[unit_id]
        if unit.state != "EXPIRED":
            raise ValueError("only expired units can be requeued")
        unit.state = "QUEUED"
        unit.worker_id = None

    def mark_expired(self, unit_id: str) -> None:
        unit = self.units[unit_id]
        if unit.state != "CLAIMED":
            raise ValueError("only claimed units can expire")
        unit.state = "EXPIRED"
        unit.worker_id = None

    def blocked(self) -> list[QueueUnit]:
        return [
            u for u in self.units.values()
            if u.state == "QUEUED"
            and any(dep not in self.units or self.units[dep].state not in {"VERIFIED_COMPLETED"} for dep in u.depends_on)
        ]

    def all_verified(self) -> bool:
        return bool(self.units) and all(
            u.state == "VERIFIED_COMPLETED" for u in self.units.values()
        )
