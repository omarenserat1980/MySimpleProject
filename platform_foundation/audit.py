from __future__ import annotations

from dataclasses import asdict, dataclass
from time import time
from typing import Any


@dataclass(frozen=True)
class EvidenceEvent:
    sequence: int
    timestamp: float
    event: str
    payload: dict[str, Any]


class EvidenceLedger:
    """Append-only evidence ledger for the foundation's first verification gate."""

    def __init__(self) -> None:
        self._events: list[EvidenceEvent] = []

    def record(self, event: str, payload: dict[str, Any]) -> EvidenceEvent:
        if not event:
            raise ValueError("event is required")
        item = EvidenceEvent(len(self._events) + 1, time(), event, dict(payload))
        self._events.append(item)
        return item

    def events(self) -> list[dict[str, Any]]:
        return [asdict(item) for item in self._events]

    def is_ready(self) -> bool:
        return isinstance(self._events, list)
