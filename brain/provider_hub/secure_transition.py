"""Commercial transition coordinator with tamper-evident integrity."""

from __future__ import annotations

from dataclasses import dataclass

from .commercial_ledger import CommercialLedger
from .commercial_state import CommercialOrderState
from .integrity_chain import IntegrityChain


@dataclass(frozen=True)
class TransitionResult:
    order_id: str
    state: str
    ledger_entry_id: str
    integrity_hash: str


class SecureCommercialTransitionCoordinator:
    def __init__(self, ledger: CommercialLedger, integrity: IntegrityChain) -> None:
        self.ledger = ledger
        self.integrity = integrity

    def transition(
        self,
        order: CommercialOrderState,
        target: str,
        entry_id: str,
        *,
        evidence_refs: tuple[str, ...] = (),
        provider_id: str | None = None,
        amount_minor: int | None = None,
        currency: str | None = None,
    ) -> TransitionResult:
        previous = order.state
        new_state = order.transition(target, evidence_ok=bool(evidence_refs))
        try:
            self.ledger.record(
                entry_id, order.order_id, previous, new_state,
                evidence_refs=evidence_refs,
                provider_id=provider_id,
                amount_minor=amount_minor,
                currency=currency,
            )
            integrity_entry = self.integrity.append(
                entry_id, order.order_id, previous, new_state,
                evidence_refs=evidence_refs,
                provider_id=provider_id,
                amount_minor=amount_minor,
                currency=currency,
            )
        except Exception:
            order.state = previous
            raise
        return TransitionResult(
            order.order_id, new_state, entry_id, integrity_entry.entry_hash
        )
