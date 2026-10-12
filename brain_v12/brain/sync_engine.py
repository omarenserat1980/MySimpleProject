"""Deterministic synchronization primitives for Brain state.

Design goals:
- one canonical revision per logical record;
- idempotent event application;
- optimistic concurrency (expected revision);
- explicit conflict reporting instead of silent overwrite;
- tombstones for deletes so offline replicas converge;
- deterministic state digest for evidence/reconciliation;
- append-only change feed that replicas can replay safely.

This module is transport-agnostic. It does not publish, pay, withdraw, or perform
other external side effects.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import hashlib, json, time
from typing import Any, Iterable, Mapping

@dataclass(frozen=True)
class SyncRecord:
    key: str
    value: dict[str, Any]
    revision: int
    deleted: bool = False
    updated_at: float = field(default_factory=time.time)
    origin: str = "brain"

@dataclass(frozen=True)
class SyncEvent:
    event_id: str
    key: str
    operation: str
    revision: int
    value: dict[str, Any]
    deleted: bool
    origin: str
    timestamp: float
    prev_digest: str = "GENESIS"

    def canonical(self) -> str:
        return json.dumps({
            "event_id": self.event_id, "key": self.key, "operation": self.operation,
            "revision": self.revision, "value": self.value, "deleted": self.deleted,
            "origin": self.origin, "timestamp": self.timestamp, "prev_digest": self.prev_digest,
        }, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.canonical().encode("utf-8")).hexdigest()

class SyncConflict(RuntimeError):
    def __init__(self, key: str, expected: int | None, actual: int):
        super().__init__(f"sync conflict for {key}: expected={expected}, actual={actual}")
        self.key, self.expected, self.actual = key, expected, actual

class BrainSyncStore:
    """Small deterministic state store suitable for local, cloud, or device replicas."""

    def __init__(self, replica_id: str):
        self.replica_id = replica_id
        self._records: dict[str, SyncRecord] = {}
        self._events: list[SyncEvent] = []
        self._seen_events: set[str] = set()

    def revision(self, key: str) -> int:
        return self._records.get(key, SyncRecord(key, {}, 0)).revision

    def get(self, key: str) -> SyncRecord | None:
        return self._records.get(key)

    def _next_revision(self, key: str) -> int:
        return self.revision(key) + 1

    def _event(self, key: str, operation: str, record: SyncRecord, event_id: str) -> SyncEvent:
        return SyncEvent(
            event_id=event_id, key=key, operation=operation, revision=record.revision,
            value=dict(record.value), deleted=record.deleted, origin=record.origin,
            timestamp=record.updated_at,
            prev_digest=self._events[-1].digest if self._events else "GENESIS",
        )

    def put(self, key: str, value: Mapping[str, Any], *, expected_revision: int | None = None, event_id: str) -> SyncEvent:
        current = self.revision(key)
        if expected_revision is not None and expected_revision != current:
            raise SyncConflict(key, expected_revision, current)
        if event_id in self._seen_events:
            return next(e for e in self._events if e.event_id == event_id)
        record = SyncRecord(key, dict(value), self._next_revision(key), False, time.time(), self.replica_id)
        event = self._event(key, "upsert", record, event_id)
        self._records[key] = record
        self._seen_events.add(event_id)
        self._events.append(event)
        return event

    def delete(self, key: str, *, expected_revision: int | None = None, event_id: str) -> SyncEvent:
        current = self.revision(key)
        if expected_revision is not None and expected_revision != current:
            raise SyncConflict(key, expected_revision, current)
        if event_id in self._seen_events:
            return next(e for e in self._events if e.event_id == event_id)
        record = SyncRecord(key, {}, self._next_revision(key), True, time.time(), self.replica_id)
        event = self._event(key, "delete", record, event_id)
        self._records[key] = record
        self._seen_events.add(event_id)
        self._events.append(event)
        return event

    def export_events(self, after_revision: int = 0) -> list[SyncEvent]:
        return [e for e in self._events if e.revision > after_revision]

    def apply(self, events: Iterable[SyncEvent]) -> dict[str, int]:
        applied = duplicate = ignored = 0
        for event in events:
            if event.event_id in self._seen_events:
                duplicate += 1
                continue
            current = self.revision(event.key)
            if event.revision <= current:
                ignored += 1
                self._seen_events.add(event.event_id)
                continue
            self._records[event.key] = SyncRecord(
                event.key, dict(event.value), event.revision, event.deleted,
                event.timestamp, event.origin,
            )
            self._seen_events.add(event.event_id)
            self._events.append(event)
            applied += 1
        return {"applied": applied, "duplicate": duplicate, "ignored": ignored}

    def snapshot(self) -> dict[str, Any]:
        records = []
        for key in sorted(self._records):
            r = self._records[key]
            records.append({"key": r.key, "value": r.value, "revision": r.revision,
                             "deleted": r.deleted, "origin": r.origin})
        raw = json.dumps(records, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return {"replica_id": self.replica_id, "records": records,
                "revision_count": sum(r["revision"] for r in records),
                "digest": hashlib.sha256(raw.encode("utf-8")).hexdigest()}

    def audit_chain_valid(self) -> bool:
        previous = "GENESIS"
        for event in self._events:
            if event.prev_digest != previous:
                return False
            if event.digest != hashlib.sha256(event.canonical().encode("utf-8")).hexdigest():
                return False
            previous = event.digest
        return True
