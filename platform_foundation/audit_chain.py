from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from time import time
from typing import Any


@dataclass(frozen=True)
class ChainEvent:
    sequence: int
    timestamp: float
    event: str
    payload: dict[str, Any]
    previous_hash: str
    event_hash: str


class AuditChain:
    """Tamper-evident append-only evidence chain."""

    def __init__(self) -> None:
        self._events: list[ChainEvent] = []

    @staticmethod
    def _hash(sequence: int, timestamp: float, event: str, payload: dict[str, Any], previous_hash: str) -> str:
        body = {
            "sequence": sequence,
            "timestamp": timestamp,
            "event": event,
            "payload": payload,
            "previous_hash": previous_hash,
        }
        encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        return hashlib.sha256(encoded).hexdigest()

    def record(self, event: str, payload: dict[str, Any]) -> ChainEvent:
        if not event:
            raise ValueError("event is required")
        previous = self._events[-1].event_hash if self._events else "GENESIS"
        sequence = len(self._events) + 1
        timestamp = time()
        digest = self._hash(sequence, timestamp, event, dict(payload), previous)
        item = ChainEvent(sequence, timestamp, event, dict(payload), previous, digest)
        self._events.append(item)
        return item

    def events(self) -> list[ChainEvent]:
        return list(self._events)

    def verify(self) -> bool:
        previous = "GENESIS"
        for index, item in enumerate(self._events, start=1):
            if item.sequence != index or item.previous_hash != previous:
                return False
            expected = self._hash(item.sequence, item.timestamp, item.event, item.payload, item.previous_hash)
            if expected != item.event_hash:
                return False
            previous = item.event_hash
        return True
