"""Deterministic commercial state-machine simulation.

This is a safety test only. It never contacts a payment provider and never moves real money.
"""

from __future__ import annotations

from dataclasses import dataclass

from brain.provider_hub.evidence import CommercialEvidenceGate, Evidence


@dataclass
class OrderSimulation:
    order_id: str
    state: str = "NEW"

    def payment_verified(self, gate: CommercialEvidenceGate) -> None:
        if not gate.can_mark_payment_verified(self.order_id):
            raise RuntimeError("PAYMENT_VERIFICATION_EVIDENCE_MISSING")
        self.state = "PAYMENT_VERIFIED"

    def revenue_realized(self, gate: CommercialEvidenceGate) -> None:
        if not gate.can_mark_revenue_realized(self.order_id):
            raise RuntimeError("REVENUE_EVIDENCE_MISSING")
        if self.state != "PAYMENT_VERIFIED":
            raise RuntimeError("PAYMENT_STATE_REQUIRED")
        self.state = "REVENUE_REALIZED"

    def delivery_verified(self, gate: CommercialEvidenceGate) -> None:
        if not gate.can_mark_delivery_verified(self.order_id):
            raise RuntimeError("DELIVERY_EVIDENCE_MISSING")
        if self.state != "REVENUE_REALIZED":
            raise RuntimeError("REVENUE_STATE_REQUIRED")
        self.state = "DELIVERY_VERIFIED"


def run_safe_simulation() -> dict[str, str]:
    gate = CommercialEvidenceGate()
    order = OrderSimulation("SIM-BRAIN-MKT-0001")

    try:
        order.payment_verified(gate)
    except RuntimeError:
        pass
    else:
        raise AssertionError("payment advanced without evidence")

    gate.add(Evidence.create("sim-pay", "PAYMENT_VERIFICATION", order.order_id,
                             "simulation", "SIM-PAYMENT-1", {"test": True}))
    order.payment_verified(gate)

    try:
        order.revenue_realized(gate)
    except RuntimeError:
        pass
    else:
        raise AssertionError("revenue advanced without confirmation")

    gate.add(Evidence.create("sim-rev", "REVENUE_CONFIRMATION", order.order_id,
                             "simulation", "SIM-LEDGER-1", {"test": True}))
    order.revenue_realized(gate)

    try:
        order.delivery_verified(gate)
    except RuntimeError:
        pass
    else:
        raise AssertionError("delivery advanced without evidence")

    gate.add(Evidence.create("sim-del", "DELIVERY_VERIFICATION", order.order_id,
                             "simulation", "SIM-ARTIFACT-1", {"test": True}))
    order.delivery_verified(gate)

    return {"order_id": order.order_id, "final_state": order.state}
