"""Append-only commercial ledger for auditable order state changes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class LedgerEntry:
    entry_id: str
    order_id: str
    from_state: str
    to_state: str
    recorded_at: str
    evidence_refs: tuple[str, ...]
    provider_id: str | None
    amount_minor: int | None
    currency: str | None
    metadata: dict[str, Any]


class CommercialLedger:
    def __init__(self) -> None:
        self._entries: list[LedgerEntry] = []
        self._ids: set[str] = set()

    def record(
        self,
        entry_id: str,
        order_id: str,
        from_state: str,
        to_state: str,
        evidence_refs: tuple[str, ...] = (),
        provider_id: str | None = None,
        amount_minor: int | None = None,
        currency: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> LedgerEntry:
        if entry_id in self._ids:
            raise ValueError(f"DUPLICATE_LEDGER_ENTRY:{entry_id}")
        if amount_minor is not None and amount_minor < 0:
            raise ValueError("NEGATIVE_AMOUNT")
        entry = LedgerEntry(
            entry_id=entry_id,
            order_id=order_id,
            from_state=from_state,
            to_state=to_state,
            recorded_at=datetime.now(timezone.utc).isoformat(),
            evidence_refs=evidence_refs,
            provider_id=provider_id,
            amount_minor=amount_minor,
            currency=currency,
            metadata=metadata or {},
        )
        self._ids.add(entry_id)
        self._entries.append(entry)
        return entry

    def for_order(self, order_id: str) -> list[LedgerEntry]:
        return [entry for entry in self._entries if entry.order_id == order_id]

    def export(self) -> list[dict[str, Any]]:
        return [asdict(entry) for entry in self._entries]
