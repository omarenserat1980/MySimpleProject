from brain.provider_hub.commercial_state import CommercialOrderState


def test_forward_flow_requires_evidence():
    order = CommercialOrderState("o1")
    for state in ("PAYMENT_VERIFIED", "REVENUE_REALIZED", "DELIVERY_VERIFIED", "COMPLETED"):
        try:
            order.transition(state)
        except ValueError as exc:
            assert str(exc) == f"EVIDENCE_REQUIRED:{state}"
        else:
            raise AssertionError("unsafe transition accepted")

    assert order.transition("PAYMENT_VERIFIED", evidence_ok=True) == "PAYMENT_VERIFIED"
    assert order.transition("REVENUE_REALIZED", evidence_ok=True) == "REVENUE_REALIZED"
    assert order.transition("DELIVERY_VERIFIED", evidence_ok=True) == "DELIVERY_VERIFIED"
    assert order.transition("COMPLETED", evidence_ok=True) == "COMPLETED"


def test_cannot_skip_states():
    order = CommercialOrderState("o2")
    try:
        order.transition("COMPLETED", evidence_ok=True)
    except ValueError as exc:
        assert str(exc) == "INVALID_TRANSITION:NEW->COMPLETED"
    else:
        raise AssertionError("state skipping accepted")


def test_refund_is_not_a_success():
    order = CommercialOrderState("o3")
    order.transition("PAYMENT_VERIFIED", evidence_ok=True)
    assert order.transition("REFUNDED") == "REFUNDED"
    try:
        order.transition("COMPLETED", evidence_ok=True)
    except ValueError as exc:
        assert str(exc) == "INVALID_TRANSITION:REFUNDED->COMPLETED"
    else:
        raise AssertionError("refunded order completed")
