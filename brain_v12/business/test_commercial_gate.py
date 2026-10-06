from brain_v12.business.commercial_control_plane import (
    CommercialCase,
    CommercialEvidence,
    CommercialState,
    profit_claim_allowed,
    revenue_claim_allowed,
)


def valid_evidence():
    return [
        CommercialEvidence("offer", "offer-001", True, "OFFER_RECORD"),
        CommercialEvidence("customer_acceptance", "accept-001", True, "CUSTOMER_ACCEPTANCE"),
        CommercialEvidence("order", "order-001", True, "ORDER_RECORD"),
        CommercialEvidence("delivery", "delivery-001", True, "DELIVERY_RECORD"),
        CommercialEvidence("payment", "payment-001", True, "PAYMENT_RECEIPT"),
    ]


def test_prospect_is_not_revenue():
    case = CommercialCase(client_id="CL-000003")
    assert case.state == CommercialState.PROSPECT
    assert not revenue_claim_allowed(case)


def test_direct_revenue_state_without_evidence_is_rejected():
    forged = CommercialCase(client_id="CL-000003", state=CommercialState.REVENUE_REALIZED)
    assert not forged.state_integrity_ok()
    assert not revenue_claim_allowed(forged)


def test_verified_flag_without_approved_provenance_is_rejected():
    evidence = valid_evidence()
    evidence[-1] = CommercialEvidence("payment", "payment-001", True, "INTERNAL_NOTE")
    forged = CommercialCase(
        client_id="CL-000003",
        state=CommercialState.REVENUE_REALIZED,
        evidence=evidence,
    )
    assert not forged.state_integrity_ok()
    assert not revenue_claim_allowed(forged)


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
    case = CommercialCase(client_id="CL-000003", evidence=valid_evidence())
    case.transition(CommercialState.REVENUE_REALIZED)
    assert case.state == CommercialState.REVENUE_REALIZED
    assert revenue_claim_allowed(case)


def test_profit_requires_cost_and_reconciliation():
    case = CommercialCase(
        client_id="CL-000003",
        state=CommercialState.REVENUE_REALIZED,
        evidence=valid_evidence(),
    )
    assert not profit_claim_allowed(case)
    try:
        case.transition(CommercialState.PROFIT_VERIFIED)
    except ValueError:
        pass
    else:
        raise AssertionError("Profit must be blocked without cost/reconciliation evidence.")
