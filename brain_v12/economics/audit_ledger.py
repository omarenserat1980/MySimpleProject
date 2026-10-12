"""Append-only economic audit ledger primitives."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    event_type: str
    opportunity_id: str
    occurred_at: str
    payload_hash: str


def payload_fingerprint(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()


def create_audit_event(
    *,
    event_type: str,
    opportunity_id: str,
    payload: dict,
    occurred_at: str | None = None,
) -> AuditEvent:
    if not event_type.strip():
        raise ValueError("event_type cannot be empty")
    if not opportunity_id.strip():
        raise ValueError("opportunity_id cannot be empty")

    timestamp = occurred_at or datetime.now(timezone.utc).isoformat()
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid occurred_at") from exc
    if parsed.tzinfo is None:
        raise ValueError("occurred_at must include timezone")

    fingerprint = payload_fingerprint(payload)
    event_id = sha256(
        f"{event_type}|{opportunity_id}|{timestamp}|{fingerprint}".encode("utf-8")
    ).hexdigest()

    return AuditEvent(
        event_id=event_id,
        event_type=event_type,
        opportunity_id=opportunity_id,
        occurred_at=timestamp,
        payload_hash=fingerprint,
    )


def is_duplicate(event: AuditEvent, existing_event_ids: set[str]) -> bool:
    return event.event_id in existing_event_ids
