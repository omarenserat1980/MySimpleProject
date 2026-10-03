"""Jet Brain company operating system: evidence-first business execution state."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

@dataclass(frozen=True)
class BusinessUnit:
    id: str
    name: str
    mission: str
    services: tuple[str, ...]

UNITS = (
    BusinessUnit("STUDIOS","Jet Brain Studios","Media and cinematic production",("video","design")),
    BusinessUnit("AI","Jet Brain AI","AI agents and intelligent automation",("ai","automation")),
    BusinessUnit("SOFTWARE","Jet Brain Software","Web, apps, APIs, SaaS and IT services",("websites","apps","software","it")),
    BusinessUnit("MARKETING","Jet Brain Marketing","Evidence-backed customer acquisition",("marketing","seo","social")),
    BusinessUnit("COMMERCE","Jet Brain Commerce","Digital products and commerce systems",("commerce",)),
    BusinessUnit("INTELLIGENCE","Jet Brain Intelligence","Research, data and business intelligence",("data","research")),
    BusinessUnit("R_AND_D","Jet Brain R&D","Self-improvement and future evolution",()),
)

class CompanyOperatingSystem:
    def units(self) -> list[dict[str, Any]]:
        return [asdict(x) for x in UNITS]

    def service_map(self, services: list[dict[str, Any]]) -> dict[str, str]:
        by_service = {
            service_id: unit.id
            for unit in UNITS
            for service_id in unit.services
        }
        by_category = {
            service_id: unit.id
            for unit in UNITS
            for service_id in unit.services
        }
        # Prefer the canonical service id. If a catalog version uses a
        # different id but preserves the canonical category, resolve by
        # category rather than silently returning UNASSIGNED.
        category_to_unit = {
            service_id: unit.id
            for unit in UNITS
            for service_id in unit.services
        }
        result = {}
        for service in services:
            service_id = service["id"]
            unit_id = by_service.get(service_id)
            if unit_id is None:
                unit_id = category_to_unit.get(service.get("category"))
            result[service_id] = unit_id if unit_id is not None else "UNASSIGNED"
        return result

    def operating_cycle(self) -> tuple[str, ...]:
        return ("DISCOVER","QUALIFY","PLAN","AUTHORIZE","EXECUTE","VERIFY","DELIVER","MEASURE","LEARN","IMPROVE")

    def truth_rules(self) -> tuple[str, ...]:
        return (
            "capability_is_not_delivery",
            "delivery_requires_evidence",
            "revenue_requires_payment_evidence",
            "external_side_effect_requires_authorization",
        )
