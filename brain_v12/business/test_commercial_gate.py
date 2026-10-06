from decimal import Decimal

from brain_v12.business.commercial_control_plane import (
    CommercialCase,
    CommercialEvidence,
    CommercialState,
    profit_claim_allowed,
    revenue_claim_allowed,
)

VERIFIED_AT = "2026-10-06T22:00:00Z"


def evidence(evidence_type, reference, provenance, client_id="CL-000003", order_id="ORD-001", amount=100.0, currency="JOD"):
    item = CommercialEvidence(
        evidence_type, reference, True, provenance,
        client_id, order_id, amount, currency, "", VERIFIED_AT
    )
    return CommercialEvidence(
        item.evidence_type, item.reference, item.verified, item.provenance,
        item.client_id, item.order_id, item.amount, item.currency,
        item.calculated_source_digest(), item.verified_at_utc
    )


def valid_evidence(client_id="CL-000003", order_id="ORD-001", amount=100.0, currency="JOD"):
    return [
        evidence("offer", "offer-001", "OFFER_RECORD", client_id, order_id, amount, currency),
        evidence("customer_acceptance", "accept-001", "CUSTOMER_ACCEPTANCE", client_id, order_id, amount, currency),
        evidence("order", order_id, "ORDER_RECORD", client_id, order_id, amount, currency),
        evidence("delivery", "delivery-001", "DELIVERY_RECORD", client_id, order_id, amount, currency),
        evidence("payment", "payment-001", "PAYMENT_RECEIPT", client_id, order_id, amount, currency),
    ]


def configured_case(evidence_items, state=CommercialState.REVENUE_REALIZED):
    return CommercialCase(
        client_id="CL-000003",
        state=state,
        expected_order_id="ORD-001",
        expected_amount=Decimal("100.00"),
        expected_currency="JOD",
        evidence=evidence_items,
    )


def test_prospect_is_not_revenue():
    assert not revenue_claim_allowed(CommercialCase(client_id="CL-000003"))


def test_direct_revenue_state_without_evidence_is_rejected():
    case = CommercialCase(client_id="CL-000003", state=CommercialState.REVENUE_REALIZED)
    assert not revenue_claim_allowed(case)


def test_missing_client_identity_is_rejected():
    items = valid_evidence()
    items[-1] = evidence("payment", "payment-001", "PAYMENT_RECEIPT", "", "ORD-001", 100.0, "JOD")
    assert not revenue_claim_allowed(configured_case(items))


def test_missing_order_identity_is_rejected():
    items = valid_evidence()
    items[-1] = evidence("payment", "payment-001", "PAYMENT_RECEIPT", "CL-000003", "", 100.0, "JOD")
    assert not revenue_claim_allowed(configured_case(items))


def test_missing_amount_is_rejected():
    items = valid_evidence()
    items[-1] = evidence("payment", "payment-001", "PAYMENT_RECEIPT", "CL-000003", "ORD-001", None, "JOD")
    assert not revenue_claim_allowed(configured_case(items))


def test_missing_currency_is_rejected():
    items = valid_evidence()
    items[-1] = evidence("payment", "payment-001", "PAYMENT_RECEIPT", "CL-000003", "ORD-001", 100.0, "")
    assert not revenue_claim_allowed(configured_case(items))


def test_missing_source_digest_is_rejected():
    items = valid_evidence()
    original = items[-1]
    items[-1] = CommercialEvidence(
        original.evidence_type, original.reference, original.verified, original.provenance,
        original.client_id, original.order_id, original.amount, original.currency,
        "", original.verified_at_utc
    )
    assert not revenue_claim_allowed(configured_case(items))


def test_malformed_source_digest_is_rejected():
    items = valid_evidence()
    original = items[-1]
    items[-1] = CommercialEvidence(
        original.evidence_type, original.reference, original.verified, original.provenance,
        original.client_id, original.order_id, original.amount, original.currency,
        "not-a-sha256", original.verified_at_utc
    )
    assert not revenue_claim_allowed(configured_case(items))


def test_tampered_content_after_digest_is_rejected():
    items = valid_evidence()
    original = items[-1]
    tampered = CommercialEvidence(
        original.evidence_type, original.reference, original.verified, original.provenance,
        original.client_id, original.order_id, Decimal("100.01"), original.currency,
        original.source_digest, original.verified_at_utc
    )
    assert original.source_digest != tampered.calculated_source_digest()
    assert not revenue_claim_allowed(configured_case(items[:-1] + [tampered]))


def test_tampered_reference_after_digest_is_rejected():
    items = valid_evidence()
    original = items[-1]
    tampered = CommercialEvidence(
        original.evidence_type, "payment-forged", original.verified, original.provenance,
        original.client_id, original.order_id, original.amount, original.currency,
        original.source_digest, original.verified_at_utc
    )
    assert not revenue_claim_allowed(configured_case(items[:-1] + [tampered]))


def test_missing_verification_time_is_rejected():
    items = valid_evidence()
    original = items[-1]
    items[-1] = CommercialEvidence(
        original.evidence_type, original.reference, original.verified, original.provenance,
        original.client_id, original.order_id, original.amount, original.currency,
        original.source_digest, ""
    )
    assert not revenue_claim_allowed(configured_case(items))


def test_wrong_client_payment_is_rejected():
    items = valid_evidence()
    items[-1] = evidence("payment", "payment-other", "PAYMENT_RECEIPT", "CL-999999", "ORD-001", 100.0, "JOD")
    assert not revenue_claim_allowed(configured_case(items))


def test_wrong_order_payment_is_rejected():
    items = valid_evidence()
    items[-1] = evidence("payment", "payment-other", "PAYMENT_RECEIPT", "CL-000003", "ORD-999", 100.0, "JOD")
    assert not revenue_claim_allowed(configured_case(items))


def test_wrong_amount_or_currency_is_rejected():
    items = valid_evidence()
    items[-1] = evidence("payment", "payment-other", "PAYMENT_RECEIPT", "CL-000003", "ORD-001", 999.0, "USD")
    assert not revenue_claim_allowed(configured_case(items))


def test_decimal_money_representation_is_exact():
    items = valid_evidence(amount=Decimal("100.00"))
    assert revenue_claim_allowed(configured_case(items))


def test_fractional_money_mismatch_is_rejected():
    items = valid_evidence(amount=Decimal("100.01"))
    assert not revenue_claim_allowed(configured_case(items))


def test_verified_flag_without_approved_provenance_is_rejected():
    items = valid_evidence()
    items[-1] = evidence("payment", "payment-001", "INTERNAL_NOTE", "CL-000003", "ORD-001", 100.0, "JOD")
    assert not revenue_claim_allowed(configured_case(items))


def test_revenue_requires_payment_and_delivery():
    case = configured_case(valid_evidence()[:3])
    assert not revenue_claim_allowed(case)


def test_revenue_can_be_realized_only_with_required_evidence():
    case = configured_case(valid_evidence())
    case.transition(CommercialState.REVENUE_REALIZED)
    assert revenue_claim_allowed(case)


def test_profit_requires_cost_and_reconciliation():
    case = configured_case(valid_evidence(), CommercialState.REVENUE_REALIZED)
    assert not profit_claim_allowed(case)
    try:
        case.transition(CommercialState.PROFIT_VERIFIED)
    except ValueError:
        pass
    else:
        raise AssertionError("Profit must be blocked without cost/reconciliation evidence.")
