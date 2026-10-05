from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .persistent_state import SQLiteStateStore


@dataclass(frozen=True)
class OperationalState:
    phase: str
    status: str
    revision: int


class OperationalStateStore:
    """Persist the operational gate state so readiness survives process restart."""

    KEY = "platform.operational_state"

    def __init__(self, store: SQLiteStateStore) -> None:
        self.store = store

    def set(self, *, phase: str, status: str) -> OperationalState:
        if not phase or not status:
            raise ValueError("phase and status are required")

        def update(current: Any) -> tuple[bool, dict[str, Any]]:
            previous_revision = int((current or {}).get("revision", 0))
            value = {
                "phase": phase,
                "status": status,
                "revision": previous_revision + 1,
            }
            return True, value

        _, value = self.store.atomic_update(self.KEY, update, default={})
        return OperationalState(**value)

    def get(self) -> OperationalState | None:
        value = self.store.get(self.KEY)
        if not value:
            return None
        return OperationalState(**value)


__all__ = ["OperationalState", "OperationalStateStore"]
