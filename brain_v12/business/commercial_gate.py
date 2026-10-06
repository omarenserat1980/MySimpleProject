"""CI-facing commercial claim gate.

Fails closed for unsupported, malformed, contradictory, or chronologically
invalid revenue/profit claims.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from brain_v12.business.commercial_control_plane import (
    CommercialCase,
    CommercialEvidence,
    CommercialState,
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
                event_at_utc=item.get("event_at_utc", ""),
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
    return data, case


def _verified_evidence_of_type(case: CommercialCase, evidence_type: str):
    return [
        item for item in case.evidence
        if item.evidence_type == evidence_type
        and case.evidence_matches_case(item)
        and item.independently_supported()
    ]


def assert_persisted_claims_match_evidence(data, case: CommercialCase) -> None:
    revenue = data.get("revenue_claim", {})
    profit = data.get("profit_claim", {})

    revenue_allowed = revenue_claim_allowed(case)
    profit_allowed = profit_claim_allowed(case)

    revenue_status = revenue.get("status", "NOT_REALIZED")
    profit_status = profit.get("status", "NOT_VERIFIED")

    if revenue_allowed:
        if revenue_status != "REALIZED":
            raise AssertionError("Revenue state is realized but persisted revenue claim is not REALIZED.")
        payment_items = _verified_evidence_of_type(case, "payment")
        if len(payment_items) != 1:
            raise AssertionError("Exactly one independently verified payment is required for persisted revenue.")
        payment = payment_items[0]
        if _optional_decimal(revenue.get("amount")) != payment.amount:
            raise AssertionError("Persisted revenue amount does not match verified payment.")
        if (revenue.get("currency") or "").upper() != payment.currency.upper():
            raise AssertionError("Persisted revenue currency does not match verified payment.")
        if revenue.get("payment_reference") != payment.reference:
            raise AssertionError("Persisted payment reference does not match verified payment.")
    else:
        if revenue_status == "REALIZED":
            raise AssertionError("Persisted revenue claim says REALIZED without an allowed revenue claim.")

    if profit_allowed:
        if profit_status != "VERIFIED":
            raise AssertionError("Profit state is verified but persisted profit claim is not VERIFIED.")
    elif profit_status == "VERIFIED":
        raise AssertionError("Persisted profit claim says VERIFIED without an allowed profit claim.")


def assert_commercial_claims_are_supported() -> None:
    data, case = load_case()

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

    assert_persisted_claims_match_evidence(data, case)


if __name__ == "__main__":
    assert_commercial_claims_are_supported()
    print("COMMERCIAL_GATE_PASS")
