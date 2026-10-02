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
        mapping = {}
        for unit in UNITS:
            for service_id in unit.services:
                mapping[service_id] = unit.id
        return {s["id"]: mapping.get(s["id"], "UNASSIGNED") for s in services}

    def operating_cycle(self) -> tuple[str, ...]:
        return ("DISCOVER","QUALIFY","PLAN","AUTHORIZE","EXECUTE","VERIFY","DELIVER","MEASURE","LEARN","IMPROVE")

    def truth_rules(self) -> tuple[str, ...]:
        return (
            "capability_is_not_delivery",
            "delivery_requires_evidence",
            "revenue_requires_payment_evidence",
            "external_side_effect_requires_authorization",
        )
