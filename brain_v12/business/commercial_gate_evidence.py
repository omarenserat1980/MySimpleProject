"""Deterministic evidence report for the commercial gate."""

from __future__ import annotations

import json
from pathlib import Path

from brain_v12.business.commercial_control_plane import (
    CommercialCase,
    CommercialEvidence,
    CommercialState,
)

SOURCE = Path(__file__).with_name("cl_000003_evidence_record.json")


def build_report() -> dict:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    evidence = [
        CommercialEvidence(
            evidence_type=item["evidence_type"],
            reference=item["reference"],
            verified=bool(item.get("verified", False)),
        )
        for item in data.get("evidence", [])
    ]
    case = CommercialCase(
        client_id=data["client_id"],
        state=CommercialState(data["state"]),
        evidence=evidence,
    )
    verified = case.verified_types()

    return {
        "client_id": case.client_id,
        "observed_state": case.state.value,
        "verified_evidence_types": sorted(verified),
        "revenue_claim": "ALLOWED" if case.state == CommercialState.REVENUE_REALIZED else "NOT_ALLOWED",
        "profit_claim": "ALLOWED" if case.state == CommercialState.PROFIT_VERIFIED else "NOT_ALLOWED",
        "payment_evidence_present": "payment" in verified,
        "delivery_evidence_present": "delivery" in verified,
        "cost_evidence_present": "cost" in verified,
        "reconciliation_evidence_present": "reconciliation" in verified,
        "automatic_financial_side_effects": False,
        "claim_policy": "evidence_required; no inference from CI success",
    }


if __name__ == "__main__":
    print(json.dumps(build_report(), indent=2, sort_keys=True))
