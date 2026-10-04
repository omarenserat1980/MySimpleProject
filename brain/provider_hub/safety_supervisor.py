"""Commercial safety supervisor.

Orchestrates reconciliation and containment/recovery without bypassing
financial evidence gates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .audit import ProviderAuditLog, ProviderEvent
from .commercial_state import CommercialOrderState
from .containment import CommercialContainmentGate
from .evidence import CommercialEvidenceGate
from .integrity_chain import IntegrityChain
from .commercial_ledger import CommercialLedger
from .reconciliation import CommercialReconciliationEngine
from .recovery import CommercialRecoveryGate


@dataclass(frozen=True)
class SafetyDecision:
    order_id: str
    safe: bool
    action: str
    issues: tuple[str, ...]


class CommercialSafetySupervisor:
    def __init__(
        self,
        ledger: CommercialLedger,
        integrity: IntegrityChain,
        evidence: CommercialEvidenceGate,
        containment: CommercialContainmentGate,
        audit: ProviderAuditLog,
    ) -> None:
        self.reconciler = CommercialReconciliationEngine(ledger, integrity, evidence)
        self.containment = containment
        self.audit = audit
        self.recovery = CommercialRecoveryGate(containment, audit)

    def inspect(self, order: CommercialOrderState, incident_id: str) -> SafetyDecision:
        report = self.reconciler.check(order)
        if report.consistent:
            return SafetyDecision(order.order_id, True, "ALLOW", ())
        if not self.containment.is_contained(order.order_id):
            self.containment.contain(
                incident_id, order.order_id, ";".join(report.issues)
            )
            self.audit.append(ProviderEvent.create(
                f"contain-{incident_id}",
                order.order_id,
                "ORDER_CONTAINED",
                "reconciliation detected commercial inconsistency",
                metadata={"issues": report.issues},
            ))
        return SafetyDecision(order.order_id, False, "CONTAIN", report.issues)

    def recover_if_verified(
        self,
        order: CommercialOrderState,
        incident_id: str,
        verifier: Callable[[], bool],
    ) -> SafetyDecision:
        result = self.recovery.recover(incident_id, order.order_id, verifier)
        return SafetyDecision(
            order.order_id,
            result.recovered,
            "ALLOW" if result.recovered else "REMAIN_CONTAINED",
            () if result.recovered else (result.reason,),
        )
