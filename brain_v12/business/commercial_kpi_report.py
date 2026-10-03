"""Commercial KPI and evidence report for Electronic Brain.

This module summarizes evidence already recorded in the monetization registry.
It never converts forecasts, leads, opportunities, or engineering status into
revenue.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from brain_v12.business.monetization_registry import (
    COMMERCIAL_STATES,
    MonetizationEntry,
)


@dataclass(frozen=True)
class CommercialKPIReport:
    capability_count: int
    state_counts: dict[str, int]
    verified_revenue: float
    verified_costs: float
    verified_profit: float
    currency: str
    evidence_gaps: tuple[str, ...]

    def to_record(self) -> dict:
        return {
            "report_type": "BRAIN_COMMERCIAL_KPI",
            "capability_count": self.capability_count,
            "state_counts": dict(self.state_counts),
            "verified_revenue": self.verified_revenue,
            "verified_costs": self.verified_costs,
            "verified_profit": self.verified_profit,
            "currency": self.currency,
            "evidence_gaps": list(self.evidence_gaps),
            "engineering_green_is_not_revenue": True,
        }


def build_commercial_kpi_report(
    entries: Iterable[MonetizationEntry],
    *,
    currency: str = "USD",
) -> CommercialKPIReport:
    items = list(entries)
    state_counts = {state: 0 for state in COMMERCIAL_STATES}
    gaps: list[str] = []
    revenue = 0.0
    costs = 0.0

    for entry in items:
        entry.validate()
        state_counts[entry.status] += 1
        revenue += entry.realized_revenue
        costs += entry.verified_costs

        if entry.status == "MONETIZATION_PATH_DEFINED":
            gaps.append(f"{entry.capability_id}: customer evidence missing")
        elif entry.status == "CUSTOMER_VALIDATED":
            gaps.append(f"{entry.capability_id}: payment evidence missing")
        elif entry.status == "PAYMENT_VERIFIED":
            gaps.append(f"{entry.capability_id}: revenue realization evidence missing")
        elif entry.status == "REVENUE_REALIZED":
            gaps.append(f"{entry.capability_id}: attributable cost evidence missing")

    profit = revenue - costs
    return CommercialKPIReport(
        capability_count=len(items),
        state_counts=state_counts,
        verified_revenue=revenue,
        verified_costs=costs,
        verified_profit=profit,
        currency=currency,
        evidence_gaps=tuple(sorted(gaps)),
    )
