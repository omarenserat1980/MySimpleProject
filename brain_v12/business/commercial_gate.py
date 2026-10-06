"""CI-facing commercial claim gate.

Fails closed for unsupported revenue/profit claims.
"""

from __future__ import annotations

import json
from pathlib import Path

from brain_v12.business.commercial_control_plane import (
    CommercialCase,
    CommercialEvidence,
    CommercialState,
    profit_claim_allowed,
    revenue_claim_allowed,
)


EVIDENCE_FILE = Path(__file__).with_name("cl_000003_evidence_record.json")


def load_case() -> CommercialCase:
    data = json.loads(EVIDENCE_FILE.read_text(encoding="utf-8"))
    evidence = [
        CommercialEvidence(
            evidence_type=item["evidence_type"],
            reference=item["reference"],
            verified=bool(item.get("verified", False)),
        )
        for item in data.get("evidence", [])
    ]
    return CommercialCase(
        client_id=data["client_id"],
        state=CommercialState(data["state"]),
        evidence=evidence,
    )


def assert_commercial_claims_are_supported() -> None:
    case = load_case()

    if case.state == CommercialState.REVENUE_REALIZED:
        if not revenue_claim_allowed(case):
            raise AssertionError("Revenue claim is not supported by control-plane state.")

    if case.state == CommercialState.PROFIT_VERIFIED:
        if not profit_claim_allowed(case):
            raise AssertionError("Profit claim is not supported by control-plane state.")

    if case.state in {
        CommercialState.PROSPECT,
        CommercialState.OFFER_PREPARED,
        CommercialState.CUSTOMER_VALIDATED,
        CommercialState.ORDER_ACCEPTED,
        CommercialState.DELIVERY_VERIFIED,
        CommercialState.PAYMENT_VERIFIED,
    }:
        # These states must never be interpreted as realized revenue/profit.
        return


if __name__ == "__main__":
    assert_commercial_claims_are_supported()
    print("COMMERCIAL_GATE_PASS")
