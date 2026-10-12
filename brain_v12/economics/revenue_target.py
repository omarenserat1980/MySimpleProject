"""Revenue target state: target is not revenue.

This module keeps the first verified-revenue objective explicit without
allowing a target or forecast to become accounting income.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RevenueTarget:
    target_amount: float = 0.10
    currency: str = "USD"

    def __post_init__(self):
        if self.target_amount <= 0:
            raise ValueError("target_amount must be positive")
        if not self.currency.strip():
            raise ValueError("currency is required")


@dataclass(frozen=True)
class RevenueStatus:
    target: RevenueTarget
    confirmed_revenue: float
    remaining: float
    achieved: bool


def evaluate_target(
    confirmed_revenue: float,
    *,
    target: RevenueTarget = RevenueTarget(),
) -> RevenueStatus:
    if confirmed_revenue < 0:
        raise ValueError("confirmed_revenue must be non-negative")
    remaining = max(0.0, target.target_amount - confirmed_revenue)
    return RevenueStatus(
        target=target,
        confirmed_revenue=confirmed_revenue,
        remaining=remaining,
        achieved=confirmed_revenue >= target.target_amount,
    )
