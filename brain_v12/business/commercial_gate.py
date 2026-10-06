"""CI-facing commercial claim gate.

Fails closed for unsupported revenue/profit claims, malformed persisted evidence,
contradictory persisted claims, and forbidden automatic financial side effects.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from brain_v12.business.commercial_control_plane import (
    CommercialCase,
    CommercialEvidence,
    CommercialState,
    forbidden_financial_side_effect,
    profit_claim_allowed,
    revenue_claim_allowed,
)


EVIDENCE_FILE = Path(__file__).with_name("cl_000003_evidence_record.json")


def _optional_decimal(value):
    if value is None:
        return None
    return Decimal(str(value))


def load_case():
    data = json.loads(EVIDENCE_FILE.read_text(encoding="utf-8"))

    if not data.get("client_id"):
        raise AssertionError("Commercial evidence record has no client_id.")
    if not data.get("state"):
        raise AssertionError("Commercial evidence record has no state.")

    evidence = []
    for item in data.get("evidence", []):
        required = {"evidence_type", "reference", "verified", "provenance"}
        missing = sorted(required - item.keys())
        if missing:
            raise AssertionError(f"Evidence item missing fields: {missing}")

        evidence.append(
            CommercialEvidence(
                evidence_type=item["evidence_type"],
                reference=item["reference"],
                verified=bool(item["verified"]),
                provenance=item["provenance"],
                client_id=item.get("client_id", ""),
                order_id=item.get("order_id", ""),
                amount=_optional_decimal(item.get("amount")),
                currency=item.get("currency", ""),
                source_digest=item.get("source_digest", ""),
                verified_at_utc=item.get("verified_at_utc", ""),
            )
        )

    case = CommercialCase(
        client_id=data["client_id"],
        state=CommercialState(data["state"]),
        expected_order_id=data.get("expected_order_id", ""),
        expected_amount=_optional_decimal(data.get("expected_amount")),
        expected_currency=data.get("expected_currency", ""),
        evidence=evidence,
    )
    return case, data


def assert_commercial_claims_are_supported() -> None:
    case, data = load_case()

    side_effects = data.get("side_effects", {})
    forbidden = {
        name: value
        for name, value in side_effects.items()
        if bool(value) and forbidden_financial_side_effect(
            "auto_" + name.removeprefix("automatic_")
        )
    }
    if forbidden:
        raise AssertionError(f"Forbidden automatic financial side effects recorded: {sorted(forbidden)}")

    revenue_status = data.get("revenue_claim", {}).get("status", "NOT_REALIZED")
    profit_status = data.get("profit_claim", {}).get("status", "NOT_VERIFIED")

    if revenue_status == "REALIZED" and case.state != CommercialState.REVENUE_REALIZED:
        raise AssertionError("Persisted revenue claim contradicts commercial state.")
    if profit_status == "VERIFIED" and case.state != CommercialState.PROFIT_VERIFIED:
        raise AssertionError("Persisted profit claim contradicts commercial state.")

    if not case.state_integrity_ok():
        raise AssertionError(
            f"Commercial state {case.state.value} is not supported by persisted evidence."
        )

    if case.state == CommercialState.REVENUE_REALIZED and not revenue_claim_allowed(case):
        raise AssertionError("Revenue claim is not supported by the persisted evidence chain.")

    if case.state == CommercialState.PROFIT_VERIFIED and not profit_claim_allowed(case):
        raise AssertionError("Profit claim is not supported by the persisted evidence chain.")

    if case.state != CommercialState.REVENUE_REALIZED and revenue_claim_allowed(case):
        raise AssertionError("Revenue claim unexpectedly allowed before REVENUE_REALIZED.")

    if case.state != CommercialState.PROFIT_VERIFIED and profit_claim_allowed(case):
        raise AssertionError("Profit claim unexpectedly allowed before PROFIT_VERIFIED.")


if __name__ == "__main__":
    assert_commercial_claims_are_supported()
    print("COMMERCIAL_GATE_PASS")
