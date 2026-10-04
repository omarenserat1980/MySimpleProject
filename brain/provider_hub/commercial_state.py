"""Evidence-gated commercial order state machine."""

from __future__ import annotations
from dataclasses import dataclass

STATES = ("NEW","PAYMENT_VERIFIED","REVENUE_REALIZED","DELIVERY_VERIFIED","COMPLETED","FAILED","REFUNDED","CANCELLED")

FORWARD = {
    "NEW": {"PAYMENT_VERIFIED","FAILED","CANCELLED"},
    "PAYMENT_VERIFIED": {"REVENUE_REALIZED","FAILED","REFUNDED","CANCELLED"},
    "REVENUE_REALIZED": {"DELIVERY_VERIFIED","FAILED","REFUNDED"},
    "DELIVERY_VERIFIED": {"COMPLETED","FAILED","REFUNDED"},
    "COMPLETED": set(),"FAILED": set(),"REFUNDED": set(),"CANCELLED": set(),
}

@dataclass
class CommercialOrderState:
    order_id: str
    state: str = "NEW"

    def transition(self, target: str, *, evidence_ok: bool = False) -> str:
        if target not in STATES:
            raise ValueError(f"INVALID_STATE:{target}")
        if target in {"PAYMENT_VERIFIED","REVENUE_REALIZED","DELIVERY_VERIFIED","COMPLETED"} and not evidence_ok:
            raise ValueError(f"EVIDENCE_REQUIRED:{target}")
        if target not in FORWARD[self.state]:
            raise ValueError(f"INVALID_TRANSITION:{self.state}->{target}")
        self.state = target
        return self.state
