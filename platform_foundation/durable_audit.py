from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from time import time
from typing import Any


@dataclass(frozen=True)
class DurableChainEvent:
    sequence: int
    timestamp: float
    event: str
    payload: dict[str, Any]
    previous_hash: str
    event_hash: str


class SQLiteAuditChain:
    """Durable tamper-evident append-only audit chain.

    Unlike the in-memory AuditChain, this implementation survives process restart.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS audit_events (
                sequence INTEGER PRIMARY KEY,
                timestamp REAL NOT NULL,
                event TEXT NOT NULL,
                payload TEXT NOT NULL,
                previous_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL
            )"""
        )
        self._conn.commit()
        self._lock = threading.RLock()

    @staticmethod
    def _hash(
        sequence: int,
        timestamp: float,
        event: str,
        payload: dict[str, Any],
        previous_hash: str,
    ) -> str:
        body = {
            "sequence": sequence,
            "timestamp": timestamp,
            "event": event,
            "payload": payload,
            "previous_hash": previous_hash,
        }
        encoded = json.dumps(
            body, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
        return hashlib.sha256(encoded).hexdigest()

    def record(self, event: str, payload: dict[str, Any]) -> DurableChainEvent:
        if not event:
            raise ValueError("event is required")
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT sequence,event_hash FROM audit_events ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            previous = row[1] if row else "GENESIS"
            sequence = (int(row[0]) + 1) if row else 1
            timestamp = time()
            data = dict(payload)
            digest = self._hash(sequence, timestamp, event, data, previous)
            self._conn.execute(
                "INSERT INTO audit_events(sequence,timestamp,event,payload,previous_hash,event_hash) "
                "VALUES(?,?,?,?,?,?)",
                (
                    sequence,
                    timestamp,
                    event,
                    json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
                    previous,
                    digest,
                ),
            )
            return DurableChainEvent(sequence, timestamp, event, data, previous, digest)

    def append(self, event: str, payload: dict[str, Any]) -> DurableChainEvent:
        return self.record(event, payload)

    def events(self) -> list[DurableChainEvent]:
        rows = self._conn.execute(
            "SELECT sequence,timestamp,event,payload,previous_hash,event_hash "
            "FROM audit_events ORDER BY sequence"
        ).fetchall()
        return [
            DurableChainEvent(
                int(sequence),
                float(timestamp),
                event,
                json.loads(payload),
                previous_hash,
                event_hash,
            )
            for sequence, timestamp, event, payload, previous_hash, event_hash in rows
        ]

    def verify(self) -> bool:
        previous = "GENESIS"
        for index, item in enumerate(self.events(), start=1):
            if item.sequence != index or item.previous_hash != previous:
                return False
            expected = self._hash(
                item.sequence,
                item.timestamp,
                item.event,
                item.payload,
                item.previous_hash,
            )
            if expected != item.event_hash:
                return False
            previous = item.event_hash
        return True

    def close(self) -> None:
        self._conn.close()


__all__ = ["DurableChainEvent", "SQLiteAuditChain"]
