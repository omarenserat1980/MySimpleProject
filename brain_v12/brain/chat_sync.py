"""Multi-device chat synchronization primitives.

The Brain chat database is authoritative when devices connect to the same
Brain service. Devices use stable IDs and client event IDs so offline writes
can be retried without duplicating messages.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class ChatSyncEvent:
    event_id: str
    session_id: str
    event_type: str
    payload: dict[str, Any]
    device_id: str

    @classmethod
    def new(cls, session_id: str, event_type: str, payload: dict[str, Any], device_id: str) -> "ChatSyncEvent":
        return cls(str(uuid4()), session_id, event_type, dict(payload), device_id)


def normalize_device_id(device_id: str | None) -> str:
    value = str(device_id or "").strip()
    if not value:
        raise ValueError("device_id is required for multi-device sync")
    if len(value) > 128:
        raise ValueError("device_id is too long")
    return value


def sync_contract() -> dict[str, Any]:
    return {
        "mode": "server_authoritative_event_feed",
        "offline": True,
        "idempotent": True,
        "cursor": "monotonic_server_event_id",
        "device_identity": "stable_client_device_id",
        "dedupe_key": "client_message_id",
        "conflict_policy": "append_only_messages_server_order",
        "memory_policy": "last_server_write",
    }
