"""Commercial outcome gate for Electronic Brain.

Engineering success is distinct from economic success. A monetizable Brain
capability is commercially successful only when verified revenue exists; profit
is tracked separately and is never inferred from forecasts.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CommercialOutcome:
    capability_id: str
    monetization_path: str
    customer_or_buyer_evidence: bool = False
    payment_verified: bool = False
    revenue_realized: bool = False
    realized_amount: float | None = None
    currency: str = "USD"
    costs_verified: float | None = None
    profit_verified: bool = False
    evidence_refs: list[str] = field(default_factory=list)

    def status(self) -> str:
        if self.profit_verified and self.revenue_realized:
            return "PROFIT_VERIFIED"
        if self.revenue_realized:
            return "REVENUE_REALIZED"
        if self.payment_verified:
            return "PAYMENT_VERIFIED"
        if self.customer_or_buyer_evidence:
            return "CUSTOMER_VALIDATED"
        return "MONETIZATION_PATH_DEFINED"

    def success_contract(self) -> dict:
        return {
            "capability_id": self.capability_id,
            "status": self.status(),
            "engineering_green_is_not_revenue": True,
            "revenue_success_requires_verified_payment": True,
            "profit_success_requires_verified_revenue_and_costs": True,
            "automatic_purchase": False,
            "automatic_contract": False,
            "automatic_withdrawal": False,
            "funds_moved_by_brain": False,
            "evidence_refs": list(self.evidence_refs),
        }


def evaluate_commercial_outcome(outcome: CommercialOutcome) -> dict:
    if not outcome.capability_id.strip():
        raise ValueError("capability_id required")
    if not outcome.monetization_path.strip():
        raise ValueError("monetization_path required")
    if outcome.revenue_realized and not outcome.payment_verified:
        raise ValueError("revenue_realized requires payment_verified")
    if outcome.profit_verified:
        if not outcome.revenue_realized:
            raise ValueError("profit_verified requires revenue_realized")
        if outcome.costs_verified is None:
            raise ValueError("profit_verified requires verified costs")
    if outcome.revenue_realized and outcome.realized_amount is None:
        raise ValueError("realized_amount required for revenue realization")
    return outcome.success_contract()
