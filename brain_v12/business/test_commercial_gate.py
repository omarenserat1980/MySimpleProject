from decimal import Decimal

from brain_v12.business.commercial_control_plane import (
    CommercialCase,
    CommercialEvidence,
    CommercialState,
    profit_claim_allowed,
    revenue_claim_allowed,
)


def valid_evidence(client_id="CL-000003", order_id="ORD-001", amount=100.0, currency="JOD"):
    return [
        CommercialEvidence("offer", "offer-001", True, "OFFER_RECORD", client_id, order_id, amount, currency),
        CommercialEvidence("customer_acceptance", "accept-001", True, "CUSTOMER_ACCEPTANCE", client_id, order_id, amount, currency),
        CommercialEvidence("order", order_id, True, "ORDER_RECORD", client_id, order_id, amount, currency),
        CommercialEvidence("delivery", "delivery-001", True, "DELIVERY_RECORD", client_id, order_id, amount, currency),
        CommercialEvidence("payment", "payment-001", True, "PAYMENT_RECEIPT", client_id, order_id, amount, currency),
    ]


def configured_case(evidence, state=CommercialState.REVENUE_REALIZED):
    return CommercialCase(
        client_id="CL-000003",
        state=state,
        expected_order_id="ORD-001",
        expected_amount=Decimal("100.00"),
        expected_currency="JOD",
        evidence=evidence,
    )


def test_prospect_is_not_revenue():
    assert not revenue_claim_allowed(CommercialCase(client_id="CL-000003"))


def test_direct_revenue_state_without_evidence_is_rejected():
    case = CommercialCase(client_id="CL-000003", state=CommercialState.REVENUE_REALIZED)
    assert not case.state_integrity_ok()
    assert not revenue_claim_allowed(case)


def test_missing_client_identity_is_rejected():
    evidence = valid_evidence()
    evidence[-1] = CommercialEvidence("payment", "payment-001", True, "PAYMENT_RECEIPT", "", "ORD-001", 100.0, "JOD")
    assert not revenue_claim_allowed(configured_case(evidence))


def test_missing_order_identity_is_rejected():
    evidence = valid_evidence()
    evidence[-1] = CommercialEvidence("payment", "payment-001", True, "PAYMENT_RECEIPT", "CL-000003", "", 100.0, "JOD")
    assert not revenue_claim_allowed(configured_case(evidence))


def test_missing_amount_is_rejected():
    evidence = valid_evidence()
    evidence[-1] = CommercialEvidence("payment", "payment-001", True, "PAYMENT_RECEIPT", "CL-000003", "ORD-001", None, "JOD")
    assert not revenue_claim_allowed(configured_case(evidence))


def test_missing_currency_is_rejected():
    evidence = valid_evidence()
    evidence[-1] = CommercialEvidence("payment", "payment-001", True, "PAYMENT_RECEIPT", "CL-000003", "ORD-001", 100.0, "")
    assert not revenue_claim_allowed(configured_case(evidence))


def test_wrong_client_payment_is_rejected():
    evidence = valid_evidence()
    evidence[-1] = CommercialEvidence("payment", "payment-other", True, "PAYMENT_RECEIPT", "CL-999999", "ORD-001", 100.0, "JOD")
    assert not revenue_claim_allowed(configured_case(evidence))


def test_wrong_order_payment_is_rejected():
    evidence = valid_evidence()
    evidence[-1] = CommercialEvidence("payment", "payment-other", True, "PAYMENT_RECEIPT", "CL-000003", "ORD-999", 100.0, "JOD")
    assert not revenue_claim_allowed(configured_case(evidence))


def test_wrong_amount_or_currency_is_rejected():
    evidence = valid_evidence()
    evidence[-1] = CommercialEvidence("payment", "payment-other", True, "PAYMENT_RECEIPT", "CL-000003", "ORD-001", 999.0, "USD")
    assert not revenue_claim_allowed(configured_case(evidence))


def test_decimal_money_representation_is_exact():
    evidence = valid_evidence(amount=Decimal("100.00"))
    assert revenue_claim_allowed(configured_case(evidence))


def test_fractional_money_mismatch_is_rejected():
    evidence = valid_evidence(amount=Decimal("100.01"))
    assert not revenue_claim_allowed(configured_case(evidence))


def test_verified_flag_without_approved_provenance_is_rejected():
    evidence = valid_evidence()
    evidence[-1] = CommercialEvidence("payment", "payment-001", True, "INTERNAL_NOTE", "CL-000003", "ORD-001", 100.0, "JOD")
    assert not revenue_claim_allowed(configured_case(evidence))


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
