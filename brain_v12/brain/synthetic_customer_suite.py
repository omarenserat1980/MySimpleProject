"""Synthetic Customer scenario suite for bounded, repeatable multi-client testing."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from .synthetic_customer import SyntheticExecutiveProfile


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    customer_type: str
    level: int
    request: str


DEFAULT_SCENARIOS = (
    Scenario("company-basic", "TEST_CUSTOMER_COMPANY", 1, "Build a test company service request website."),
    Scenario("student-project", "TEST_CUSTOMER_STUDENT", 1, "Validate a graduation project workflow end to end in a sandbox."),
    Scenario("creator-content", "TEST_CUSTOMER_CONTENT_CREATOR", 2, "Prepare a test content workflow and verify its output."),
    Scenario("software-multi-step", "TEST_CUSTOMER_SOFTWARE", 3, "Build and verify a multi-step test software workflow."),
    Scenario("media-cinematic", "TEST_CUSTOMER_MEDIA", 3, "Produce and verify a sandbox cinematic media workflow."),
    Scenario("startup-multi-service", "TEST_CUSTOMER_STARTUP", 4, "Exercise a multi-service startup workflow with verification."),
    Scenario("full-e2e", "TEST_CUSTOMER_FILM_PRODUCER", 5, "Run the complete sandbox customer lifecycle through delivery."),
    Scenario("executive-business", "TEST_CUSTOMER_EXECUTIVE", 5, "Evaluate strategy, pricing, marketing, finance, software and operations as one integrated sandbox business."),
    Scenario("social-marketing", "TEST_CUSTOMER_MARKETING", 4, "Plan, execute and verify a sandbox social media and performance marketing campaign."),
    Scenario("finance-operations", "TEST_CUSTOMER_FINANCE", 4, "Evaluate a sandbox financial planning, pricing, unit economics and operations workflow."),
)


class SyntheticCustomerScenarioSuite:
    def __init__(self, customer_factory, scenarios=DEFAULT_SCENARIOS):
        self.customer_factory = customer_factory
        self.scenarios = tuple(scenarios)
        self.executive_profile = SyntheticExecutiveProfile()

    def plan(self, limit: int | None = None) -> dict[str, Any]:
        selected = self.scenarios[:limit] if limit else self.scenarios
        return {
            "scenario_count": len(selected),
            "levels": sorted({x.level for x in selected}),
            "scenarios": [x.__dict__ for x in selected],
            "execution_mode": "BOUNDED_TEST",
            "production_allowed": False,
            "executive_profile": self.executive_profile.as_dict(),
        }

    def run(self, capabilities: dict[str, Any] | None = None, limit: int | None = None) -> dict[str, Any]:
        selected = self.scenarios[:limit] if limit else self.scenarios
        results = []
        for scenario in selected:
            customer = self.customer_factory()
            run = customer.start(scenario.customer_type, scenario.request)
            proposals = customer.generate_proposals(run, capabilities or {})
            results.append({
                "scenario_id": scenario.scenario_id,
                "level": scenario.level,
                "run_id": run.run_id,
                "status": run.status,
                "proposal_ready": bool(proposals.get("unified")),
                "approval_required": bool(proposals.get("unified", {}).get("approval_required")),
            })
        return {"ok": all(x["proposal_ready"] for x in results), "results": results, "count": len(results)}
