"""Commercial operations dashboard data model for Electronic Brain."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from brain_v12.business.commercial_case import CommercialCase
from brain_v12.business.monetization_registry import MonetizationEntry


@dataclass(frozen=True)
class CommercialOperationsDashboard:
    capabilities: int
    cases: int
    stage_counts: dict[str, int]
    revenue: float
    costs: float
    profit: float
    cases_needing_action: tuple[dict, ...]

    def to_record(self) -> dict:
        return {
            "dashboard_type": "BRAIN_COMMERCIAL_OPERATIONS",
            "capabilities": self.capabilities,
            "cases": self.cases,
            "stage_counts": dict(self.stage_counts),
            "verified_revenue": self.revenue,
            "verified_costs": self.costs,
            "verified_profit": self.profit,
            "cases_needing_action": list(self.cases_needing_action),
            "engineering_green_is_not_revenue": True,
        }


def build_commercial_operations_dashboard(
    entries: Iterable[MonetizationEntry],
    cases: Iterable[CommercialCase],
) -> CommercialOperationsDashboard:
    entry_list = list(entries)
    case_list = list(cases)

    for entry in entry_list:
        entry.validate()

    stage_counts = {
        "OFFER_DEFINED": 0,
        "PROSPECT_IDENTIFIED": 0,
        "CUSTOMER_VALIDATED": 0,
        "DELIVERY_VERIFIED": 0,
        "PAYMENT_VERIFIED": 0,
        "REVENUE_REALIZED": 0,
        "PROFIT_VERIFIED": 0,
    }
    actions: list[dict] = []

    for case in case_list:
        record = case.to_record()
        stage_counts[record["stage"]] += 1
        if record["next_evidence_required"] != "none":
            actions.append(
                {
                    "case_id": case.case_id,
                    "capability_id": case.capability_id,
                    "stage": record["stage"],
                    "next_evidence_required": record["next_evidence_required"],
                }
            )

    revenue = sum(item.realized_revenue for item in entry_list)
    costs = sum(item.verified_costs for item in entry_list)

    return CommercialOperationsDashboard(
        capabilities=len(entry_list),
        cases=len(case_list),
        stage_counts=stage_counts,
        revenue=revenue,
        costs=costs,
        profit=revenue - costs,
        cases_needing_action=tuple(actions),
    )
