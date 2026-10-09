from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
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
    """Durable tamper-evident append-only evidence chain."""

    def __init__(self, path: str | None = None) -> None:
        self.path = path
        self._events: list[ChainEvent] = []
        self._lock = threading.RLock()
        self._conn = None
        if path:
            self._conn = sqlite3.connect(path, check_same_thread=False)
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS audit_events ("
                "sequence INTEGER PRIMARY KEY, timestamp REAL NOT NULL, "
                "event TEXT NOT NULL, payload TEXT NOT NULL, "
                "previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL)"
            )
            self._conn.commit()
            self._load()

    @staticmethod
    def _hash(sequence: int, timestamp: float, event: str,
              payload: dict[str, Any], previous_hash: str) -> str:
        body = {
            "sequence": sequence, "timestamp": timestamp, "event": event,
            "payload": payload, "previous_hash": previous_hash,
        }
        encoded = json.dumps(
            body, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
        return hashlib.sha256(encoded).hexdigest()

    def _load(self) -> None:
        rows = self._conn.execute(
            "SELECT sequence,timestamp,event,payload,previous_hash,event_hash "
            "FROM audit_events ORDER BY sequence"
        ).fetchall()
        self._events = [
            ChainEvent(
                int(row[0]), float(row[1]), row[2], json.loads(row[3]),
                row[4], row[5]
            ) for row in rows
        ]

    def record(self, event: str, payload: dict[str, Any]) -> ChainEvent:
        if not event:
            raise ValueError("event is required")
        with self._lock:
            previous = self._events[-1].event_hash if self._events else "GENESIS"
            sequence = len(self._events) + 1
            timestamp = time()
            data = dict(payload)
            digest = self._hash(sequence, timestamp, event, data, previous)
            item = ChainEvent(sequence, timestamp, event, data, previous, digest)
            if self._conn is not None:
                self._conn.execute(
                    "INSERT INTO audit_events "
                    "(sequence,timestamp,event,payload,previous_hash,event_hash) "
                    "VALUES (?,?,?,?,?,?)",
                    (sequence, timestamp, event, json.dumps(
                        data, sort_keys=True, ensure_ascii=False
                    ), previous, digest),
                )
                self._conn.commit()
            self._events.append(item)
            return item

    def append(self, event: str, payload: dict[str, Any]) -> ChainEvent:
        return self.record(event, payload)

    def events(self) -> list[ChainEvent]:
        with self._lock:
            return list(self._events)

    def verify(self) -> bool:
        with self._lock:
            previous = "GENESIS"
            for index, item in enumerate(self._events, start=1):
                if item.sequence != index or item.previous_hash != previous:
                    return False
                expected = self._hash(
                    item.sequence, item.timestamp, item.event,
                    item.payload, item.previous_hash
                )
                if expected != item.event_hash:
                    return False
                previous = item.event_hash
            return True

    def close(self) -> None:
        if self._conn is not None:
            with self._lock:
                self._conn.close()
                self._conn = None
