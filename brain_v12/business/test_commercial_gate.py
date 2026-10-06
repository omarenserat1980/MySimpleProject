from brain_v12.business.commercial_control_plane import (
    CommercialCase,
    CommercialEvidence,
    CommercialState,
)


def test_prospect_is_not_revenue():
    case = CommercialCase(client_id="CL-000003")
    assert case.state == CommercialState.PROSPECT
    assert case.state != CommercialState.REVENUE_REALIZED


def test_revenue_requires_payment_and_delivery():
    case = CommercialCase(
        client_id="CL-000003",
        evidence=[
            CommercialEvidence("offer", "offer-001", True),
            CommercialEvidence("customer_acceptance", "accept-001", True),
            CommercialEvidence("order", "order-001", True),
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
        evidence=[
            CommercialEvidence("offer", "offer-001", True),
            CommercialEvidence("customer_acceptance", "accept-001", True),
            CommercialEvidence("order", "order-001", True),
            CommercialEvidence("delivery", "delivery-001", True),
            CommercialEvidence("payment", "payment-001", True),
        ],
    )

    case.transition(CommercialState.REVENUE_REALIZED)
    assert case.state == CommercialState.REVENUE_REALIZED


def test_profit_requires_cost_and_reconciliation():
    case = CommercialCase(
        client_id="CL-000003",
        state=CommercialState.REVENUE_REALIZED,
        evidence=[
            CommercialEvidence("offer", "offer-001", True),
            CommercialEvidence("customer_acceptance", "accept-001", True),
            CommercialEvidence("order", "order-001", True),
            CommercialEvidence("delivery", "delivery-001", True),
            CommercialEvidence("payment", "payment-001", True),
        ],
    )

    try:
        case.transition(CommercialState.PROFIT_VERIFIED)
    except ValueError:
        pass
    else:
        raise AssertionError("Profit must be blocked without cost/reconciliation evidence.")
