"""Smoke-check the economics package without external services."""
import json
from pathlib import Path

from .opportunity_engine import Opportunity, OpportunityState, score
from .revenue_gate import PaymentEvidence, ConfirmedRevenue


def run_smoke() -> dict:
    root = Path(__file__).parent
    data = json.loads((root / "opportunities.json").read_text(encoding="utf-8"))
    assert data["revenue_confirmed_policy"] if "revenue_confirmed_policy" in data else True
    assert data["opportunities"]

    sample = Opportunity("smoke", 100, 0.5, 0.8, 2, 0.1, 0.1)
    assert score(sample) > 0

    evidence = PaymentEvidence(
        "smoke-evidence", "smoke", 1, "USD",
        "2026-10-08T00:00:00Z", "proof://smoke"
    )
    revenue = ConfirmedRevenue.from_evidence(evidence)
    assert revenue.amount == 1

    return {
        "opportunities": len(data["opportunities"]),
        "score_positive": True,
        "payment_gate": "PASS",
        "state_terminal": OpportunityState.PAYMENT_VERIFIED.value,
    }


if __name__ == "__main__":
    print(run_smoke())
