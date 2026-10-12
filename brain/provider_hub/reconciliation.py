"""Commercial reconciliation engine.

Detects inconsistencies between state, ledger, integrity chain and evidence.
It reports; it never silently repairs financial state.
"""

from __future__ import annotations

from dataclasses import dataclass

from .commercial_ledger import CommercialLedger
from .commercial_state import CommercialOrderState
from .evidence import CommercialEvidenceGate
from .integrity_chain import IntegrityChain


@dataclass(frozen=True)
class ReconciliationReport:
    order_id: str
    consistent: bool
    issues: tuple[str, ...]


class CommercialReconciliationEngine:
    def __init__(
        self,
        ledger: CommercialLedger,
        integrity: IntegrityChain,
        evidence: CommercialEvidenceGate,
    ) -> None:
        self.ledger = ledger
        self.integrity = integrity
        self.evidence = evidence

    def check(self, order: CommercialOrderState) -> ReconciliationReport:
        issues: list[str] = []

        if not self.integrity.verify():
            issues.append("INTEGRITY_CHAIN_INVALID")

        entries = self.ledger.for_order(order.order_id)
        if order.state != "NEW" and not entries:
            issues.append("STATE_WITHOUT_LEDGER")

        if entries:
            if entries[-1].to_state != order.state:
                issues.append("STATE_LEDGER_MISMATCH")

            for entry in entries:
                if entry.to_state in {
                    "PAYMENT_VERIFIED",
                    "REVENUE_REALIZED",
                    "DELIVERY_VERIFIED",
                    "COMPLETED",
                } and not entry.evidence_refs:
                    issues.append(f"EVIDENCE_MISSING:{entry.entry_id}")

        return ReconciliationReport(
            order.order_id,
            consistent=not issues,
            issues=tuple(issues),
        )
