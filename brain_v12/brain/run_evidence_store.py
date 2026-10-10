"""Small append-only JSONL evidence journal with a tamper-evident hash chain.

This is a local integrity mechanism, not a signature or protection against an
attacker who can rewrite the entire file. Keep the journal in a trusted location.
"""
from __future__ import annotations

from pathlib import Path
from threading import RLock
from typing import Any, Mapping
import hashlib
import json
import os
import time

GENESIS = "0" * 64
_SECRET_MARKERS = ("password", "secret", "token", "authorization", "api_key", "private_key")


class EvidenceStoreError(RuntimeError):
    pass


class EvidenceConflict(EvidenceStoreError):
    pass


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")


def _redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        clean = {}
        for key, child in value.items():
            name = str(key)
            if any(marker in name.lower() for marker in _SECRET_MARKERS):
                clean[name] = "[REDACTED]"
            else:
                clean[name] = _redact(child)
        return clean
    if isinstance(value, (list, tuple)):
        return [_redact(item) for item in value]
    return value


class RunEvidenceStore:
    """Append-only event log; duplicate event IDs are idempotent only if identical."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._lock = RLock()

    def _read_verified(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        events: list[dict[str, Any]] = []
        previous = GENESIS
        seen: dict[str, str] = {}
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise EvidenceStoreError(f"JOURNAL_READ_FAILED:{exc}") from exc
        for number, line in enumerate(lines, 1):
            try:
                event = json.loads(line)
                supplied_hash = event.pop("event_hash")
                if event.get("previous_hash") != previous:
                    raise EvidenceStoreError(f"HASH_CHAIN_BROKEN_AT_LINE_{number}")
                expected = hashlib.sha256(_canonical(event)).hexdigest()
                if supplied_hash != expected:
                    raise EvidenceStoreError(f"EVENT_HASH_MISMATCH_AT_LINE_{number}")
                event["event_hash"] = supplied_hash
                event_id = event.get("event_id")
                if not event_id:
                    raise EvidenceStoreError(f"EVENT_ID_MISSING_AT_LINE_{number}")
                if event_id in seen and seen[event_id] != supplied_hash:
                    raise EvidenceConflict(f"EVENT_ID_CONFLICT_AT_LINE_{number}")
                seen[event_id] = supplied_hash
                previous = supplied_hash
                events.append(event)
            except EvidenceStoreError:
                raise
            except Exception as exc:
                raise EvidenceStoreError(f"INVALID_JOURNAL_LINE_{number}:{exc}") from exc
        return events

    def append(self, *, event_id: str, task_id: str, event_type: str,
               payload: Mapping[str, Any]) -> dict[str, Any]:
        if not event_id.strip() or not task_id.strip() or not event_type.strip():
            raise ValueError("EVENT_ID_TASK_ID_AND_EVENT_TYPE_REQUIRED")
        safe_payload = _redact(payload)
        with self._lock:
            events = self._read_verified()
            for existing in events:
                if existing["event_id"] == event_id:
                    candidate = {
                        "event_id": event_id, "task_id": task_id,
                        "event_type": event_type, "payload": safe_payload,
                    }
                    original = {k: existing[k] for k in candidate}
                    if original != candidate:
                        raise EvidenceConflict("IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_EVENT")
                    return {**existing, "duplicate": True}
            previous = events[-1]["event_hash"] if events else GENESIS
            event = {
                "sequence": len(events) + 1,
                "timestamp_unix": time.time(),
                "event_id": event_id,
                "task_id": task_id,
                "event_type": event_type,
                "payload": safe_payload,
                "previous_hash": previous,
            }
            event["event_hash"] = hashlib.sha256(_canonical(event)).hexdigest()
            self.path.parent.mkdir(parents=True, exist_ok=True)
            encoded = (_canonical(event).decode("utf-8") + "\n").encode("utf-8")
            try:
                with self.path.open("ab") as stream:
                    stream.write(encoded)
                    stream.flush()
                    os.fsync(stream.fileno())
            except OSError as exc:
                raise EvidenceStoreError(f"JOURNAL_APPEND_FAILED:{exc}") from exc
            return {**event, "duplicate": False}

    def read_all(self) -> list[dict[str, Any]]:
        with self._lock:
            return self._read_verified()
