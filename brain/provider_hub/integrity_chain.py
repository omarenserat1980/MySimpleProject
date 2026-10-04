"""Tamper-evident hash chain for the commercial ledger."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class IntegrityEntry:
    entry_id: str
    order_id: str
    from_state: str
    to_state: str
    recorded_at: str
    evidence_refs: tuple[str, ...]
    provider_id: str | None
    amount_minor: int | None
    currency: str | None
    previous_hash: str
    entry_hash: str


class IntegrityChain:
    def __init__(self) -> None:
        self._entries: list[IntegrityEntry] = []
        self._ids: set[str] = set()

    @staticmethod
    def _hash(payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def append(
        self,
        entry_id: str,
        order_id: str,
        from_state: str,
        to_state: str,
        evidence_refs: tuple[str, ...] = (),
        provider_id: str | None = None,
        amount_minor: int | None = None,
        currency: str | None = None,
    ) -> IntegrityEntry:
        if entry_id in self._ids:
            raise ValueError(f"DUPLICATE_INTEGRITY_ENTRY:{entry_id}")
        previous_hash = self._entries[-1].entry_hash if self._entries else "GENESIS"
        recorded_at = datetime.now(timezone.utc).isoformat()
        payload = {
            "entry_id": entry_id,
            "order_id": order_id,
            "from_state": from_state,
            "to_state": to_state,
            "recorded_at": recorded_at,
            "evidence_refs": evidence_refs,
            "provider_id": provider_id,
            "amount_minor": amount_minor,
            "currency": currency,
            "previous_hash": previous_hash,
        }
        entry_hash = self._hash(payload)
        entry = IntegrityEntry(**payload, entry_hash=entry_hash)
        self._entries.append(entry)
        self._ids.add(entry_id)
        return entry

    def verify(self) -> bool:
        previous = "GENESIS"
        for entry in self._entries:
            payload = {
                "entry_id": entry.entry_id,
                "order_id": entry.order_id,
                "from_state": entry.from_state,
                "to_state": entry.to_state,
                "recorded_at": entry.recorded_at,
                "evidence_refs": entry.evidence_refs,
                "provider_id": entry.provider_id,
                "amount_minor": entry.amount_minor,
                "currency": entry.currency,
                "previous_hash": entry.previous_hash,
            }
            if entry.previous_hash != previous or self._hash(payload) != entry.entry_hash:
                return False
            previous = entry.entry_hash
        return True

    def entries(self) -> list[IntegrityEntry]:
        return list(self._entries)
