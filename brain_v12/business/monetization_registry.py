"""Monetization registry for Electronic Brain capabilities.

The registry is a planning and evidence layer. It does not sell, charge,
withdraw, or move funds. It makes every monetizable capability explicit and
lets the Brain prioritize work that can close a verified commercial loop.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Iterable


COMMERCIAL_STATES = (
    "MONETIZATION_PATH_DEFINED",
    "CUSTOMER_VALIDATED",
    "PAYMENT_VERIFIED",
    "REVENUE_REALIZED",
    "PROFIT_VERIFIED",
)


@dataclass(frozen=True)
class MonetizationEntry:
    capability_id: str
    capability_name: str
    offer: str
    target_customer: str
    acquisition_channel: str
    delivery_evidence: str
    cost_model: str
    status: str = "MONETIZATION_PATH_DEFINED"
    realized_revenue: float = 0.0
    verified_costs: float = 0.0
    currency: str = "USD"
    evidence_refs: list[str] = field(default_factory=list)

    def validate(self) -> None:
        if not self.capability_id.strip():
            raise ValueError("capability_id required")
        for name, value in (
            ("capability_name", self.capability_name),
            ("offer", self.offer),
            ("target_customer", self.target_customer),
            ("acquisition_channel", self.acquisition_channel),
            ("delivery_evidence", self.delivery_evidence),
            ("cost_model", self.cost_model),
        ):
            if not value.strip():
                raise ValueError(f"{name} required")
        if self.status not in COMMERCIAL_STATES:
            raise ValueError(f"invalid commercial status: {self.status}")
        if self.realized_revenue < 0 or self.verified_costs < 0:
            raise ValueError("financial amounts cannot be negative")
        if self.status == "REVENUE_REALIZED" and self.realized_revenue <= 0:
            raise ValueError("revenue_realized requires positive verified revenue")
        if self.status == "PROFIT_VERIFIED":
            if self.realized_revenue <= 0:
                raise ValueError("profit_verified requires verified revenue")
            if self.verified_costs < 0:
                raise ValueError("profit_verified requires verified costs")

    def commercial_score(self) -> int:
        """Prioritization signal, not a political/financial guarantee."""
        self.validate()
        state_weight = {
            "MONETIZATION_PATH_DEFINED": 1,
            "CUSTOMER_VALIDATED": 2,
            "PAYMENT_VERIFIED": 3,
            "REVENUE_REALIZED": 4,
            "PROFIT_VERIFIED": 5,
        }[self.status]
        evidence_weight = min(len(self.evidence_refs), 3)
        return state_weight * 10 + evidence_weight

    def to_record(self) -> dict:
        self.validate()
        return asdict(self) | {
            "commercial_score": self.commercial_score(),
            "automatic_purchase": False,
            "automatic_contract": False,
            "automatic_withdrawal": False,
            "funds_moved_by_brain": False,
        }


def rank_monetization_entries(entries: Iterable[MonetizationEntry]) -> list[dict]:
    records = [entry.to_record() for entry in entries]
    return sorted(
        records,
        key=lambda item: (item["commercial_score"], item["capability_id"]),
        reverse=True,
    )
