"""Provider operational audit log.

Append-only in-process event model; persistence is delegated to BRAIN storage.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class ProviderEvent:
    event_id: str
    provider_id: str
    event_type: str
    timestamp: str
    reason: str
    evidence_ref: str | None
    metadata: dict[str, Any]

    @classmethod
    def create(
        cls,
        event_id: str,
        provider_id: str,
        event_type: str,
        reason: str,
        evidence_ref: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "ProviderEvent":
        return cls(
            event_id,
            provider_id,
            event_type,
            datetime.now(timezone.utc).isoformat(),
            reason,
            evidence_ref,
            metadata or {},
        )


class ProviderAuditLog:
    def __init__(self) -> None:
        self._events: list[ProviderEvent] = []
        self._ids: set[str] = set()

    def append(self, event: ProviderEvent) -> None:
        if event.event_id in self._ids:
            raise ValueError(f"DUPLICATE_EVENT:{event.event_id}")
        self._ids.add(event.event_id)
        self._events.append(event)

    def events_for(self, provider_id: str) -> list[ProviderEvent]:
        return [e for e in self._events if e.provider_id == provider_id]

    def export(self) -> list[dict[str, Any]]:
        return [asdict(e) for e in self._events]
