from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from time import time
from typing import Any
from uuid import uuid4

from .persistent_state import SQLiteStateStore


class MemoryKind(str, Enum):
    FACT = "FACT"
    PREFERENCE = "PREFERENCE"
    PROJECT_REQUIREMENT = "PROJECT_REQUIREMENT"
    DECISION = "DECISION"
    TASK = "TASK"
    EVENT = "EVENT"
    AUDIT = "AUDIT"
    TEMPORARY_STATE = "TEMPORARY_STATE"


@dataclass(frozen=True)
class MemoryRecord:
    memory_id: str
    kind: str
    key: str
    value: Any
    source: str
    confidence: float
    created_at: float
    updated_at: float
    active: bool = True
    expires_at: float | None = None


class MemoryEngine:
    """Durable, typed memory with provenance, confidence and soft-forget semantics."""

    KEY = "platform.memory.records"

    def __init__(self, store: SQLiteStateStore) -> None:
        self.store = store

    @staticmethod
    def _validate(kind: MemoryKind | str, key: str, source: str, confidence: float) -> str:
        normalized = kind.value if isinstance(kind, MemoryKind) else str(kind)
        if normalized not in {item.value for item in MemoryKind}:
            raise ValueError("unsupported memory kind")
        if not key:
            raise ValueError("memory key is required")
        if not source:
            raise ValueError("memory source is required")
        if not 0.0 <= float(confidence) <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        return normalized

    def remember(
        self,
        *,
        kind: MemoryKind | str,
        key: str,
        value: Any,
        source: str,
        confidence: float = 1.0,
        expires_at: float | None = None,
    ) -> MemoryRecord:
        normalized = self._validate(kind, key, source, confidence)
        now = time()
        holder: dict[str, Any] = {}

        def update(current: Any) -> tuple[bool, dict[str, Any]]:
            records = dict(current or {})
            existing = next(
                (item for item in records.values()
                 if item["active"] and item["kind"] == normalized and item["key"] == key),
                None,
            )
            memory_id = existing["memory_id"] if existing else str(uuid4())
            created_at = existing["created_at"] if existing else now
            record = MemoryRecord(
                memory_id=memory_id,
                kind=normalized,
                key=key,
                value=value,
                source=source,
                confidence=float(confidence),
                created_at=created_at,
                updated_at=now,
                active=True,
                expires_at=expires_at,
            )
            records[memory_id] = asdict(record)
            holder["record"] = record
            return True, records

        self.store.atomic_update(self.KEY, update, default={})
        return holder["record"]

    def get(self, *, kind: MemoryKind | str, key: str, include_expired: bool = False) -> MemoryRecord | None:
        normalized = kind.value if isinstance(kind, MemoryKind) else str(kind)
        records = self.store.get(self.KEY, {})
        now = time()
        matches = []
        for item in records.values():
            if item["kind"] != normalized or item["key"] != key or not item["active"]:
                continue
            if not include_expired and item.get("expires_at") is not None and item["expires_at"] <= now:
                continue
            matches.append(MemoryRecord(**item))
        return max(matches, key=lambda item: item.updated_at, default=None)

    def list(self, *, kind: MemoryKind | str | None = None, include_inactive: bool = False) -> list[MemoryRecord]:
        normalized = kind.value if isinstance(kind, MemoryKind) else (str(kind) if kind is not None else None)
        now = time()
        result = []
        for item in self.store.get(self.KEY, {}).values():
            record = MemoryRecord(**item)
            if normalized is not None and record.kind != normalized:
                continue
            if not include_inactive and not record.active:
                continue
            if record.active and record.expires_at is not None and record.expires_at <= now:
                continue
            result.append(record)
        return sorted(result, key=lambda item: (item.kind, item.key, item.updated_at))

    def forget(self, memory_id: str) -> bool:
        if not memory_id:
            raise ValueError("memory_id is required")

        def update(current: Any) -> tuple[bool, dict[str, Any]]:
            records = dict(current or {})
            item = records.get(memory_id)
            if item is None or not item["active"]:
                return False, records
            item = dict(item)
            item["active"] = False
            item["updated_at"] = time()
            records[memory_id] = item
            return True, records

        changed, _ = self.store.atomic_update(self.KEY, update, default={})
        return changed

    def is_ready(self) -> bool:
        return self.store.is_ready()


__all__ = ["MemoryEngine", "MemoryKind", "MemoryRecord"]
