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


def test_prospect_is_not_revenue():
    case = CommercialCase(client_id="CL-000003")
    assert not revenue_claim_allowed(case)


def test_direct_revenue_state_without_evidence_is_rejected():
    forged = CommercialCase(client_id="CL-000003", state=CommercialState.REVENUE_REALIZED)
    assert not forged.state_integrity_ok()
    assert not revenue_claim_allowed(forged)


def test_wrong_client_payment_is_rejected():
    evidence = valid_evidence()
    evidence[-1] = CommercialEvidence(
        "payment", "payment-other", True, "PAYMENT_RECEIPT",
        "CL-999999", "ORD-001", 100.0, "JOD"
    )
    case = CommercialCase(
        client_id="CL-000003",
        state=CommercialState.REVENUE_REALIZED,
        expected_order_id="ORD-001",
        expected_amount=100.0,
        expected_currency="JOD",
        evidence=evidence,
    )
    assert not revenue_claim_allowed(case)


def test_wrong_order_payment_is_rejected():
    evidence = valid_evidence()
    evidence[-1] = CommercialEvidence(
        "payment", "payment-other", True, "PAYMENT_RECEIPT",
        "CL-000003", "ORD-999", 100.0, "JOD"
    )
    case = CommercialCase(
        client_id="CL-000003",
        state=CommercialState.REVENUE_REALIZED,
        expected_order_id="ORD-001",
        expected_amount=100.0,
        expected_currency="JOD",
        evidence=evidence,
    )
    assert not revenue_claim_allowed(case)


def test_wrong_amount_or_currency_is_rejected():
    evidence = valid_evidence()
    evidence[-1] = CommercialEvidence(
        "payment", "payment-other", True, "PAYMENT_RECEIPT",
        "CL-000003", "ORD-001", 999.0, "USD"
    )
    case = CommercialCase(
        client_id="CL-000003",
        state=CommercialState.REVENUE_REALIZED,
        expected_order_id="ORD-001",
        expected_amount=100.0,
        expected_currency="JOD",
        evidence=evidence,
    )
    assert not revenue_claim_allowed(case)


def test_verified_flag_without_approved_provenance_is_rejected():
    evidence = valid_evidence()
    evidence[-1] = CommercialEvidence(
        "payment", "payment-001", True, "INTERNAL_NOTE",
        "CL-000003", "ORD-001", 100.0, "JOD"
    )
    case = CommercialCase(
        client_id="CL-000003",
        state=CommercialState.REVENUE_REALIZED,
        expected_order_id="ORD-001",
        expected_amount=100.0,
        expected_currency="JOD",
        evidence=evidence,
    )
    assert not revenue_claim_allowed(case)


def test_revenue_requires_payment_and_delivery():
    case = CommercialCase(
        client_id="CL-000003",
        evidence=[
            CommercialEvidence("offer", "offer-001", True, "OFFER_RECORD"),
            CommercialEvidence("customer_acceptance", "accept-001", True, "CUSTOMER_ACCEPTANCE"),
            CommercialEvidence("order", "order-001", True, "ORDER_RECORD"),
        ],
    )
    try:
        case.transition(CommercialState.REVENUE_REALIZED)
    except ValueError:
        pass
    else:
        raise AssertionError("Revenue must be blocked without delivery/payment evidence.")


def test_revenue_can_be_realized_only_with_required_evidence():
    case = CommercialCase(
        client_id="CL-000003",
        evidence=valid_evidence(),
        expected_order_id="ORD-001",
        expected_amount=100.0,
        expected_currency="JOD",
    )
    case.transition(CommercialState.REVENUE_REALIZED)
    assert revenue_claim_allowed(case)


def test_profit_requires_cost_and_reconciliation():
    case = CommercialCase(
        client_id="CL-000003",
        state=CommercialState.REVENUE_REALIZED,
        evidence=valid_evidence(),
        expected_order_id="ORD-001",
        expected_amount=100.0,
        expected_currency="JOD",
    )
    assert not profit_claim_allowed(case)
    try:
        case.transition(CommercialState.PROFIT_VERIFIED)
    except ValueError:
        pass
    else:
        raise AssertionError("Profit must be blocked without cost/reconciliation evidence.")
