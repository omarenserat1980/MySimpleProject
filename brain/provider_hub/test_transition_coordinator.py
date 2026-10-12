import pytest

from brain.provider_hub.commercial_ledger import CommercialLedger
from brain.provider_hub.commercial_state import CommercialOrderState
from brain.provider_hub.transition_coordinator import CommercialTransitionCoordinator


def test_valid_transition_is_recorded():
    order = CommercialOrderState("o1")
    ledger = CommercialLedger()
    c = CommercialTransitionCoordinator(ledger)
    result = c.transition(order, "PAYMENT_VERIFIED", "l1", evidence_refs=("pay-1",))
    assert result.state == "PAYMENT_VERIFIED"
    assert ledger.for_order("o1")[0].to_state == "PAYMENT_VERIFIED"


def test_invalid_transition_is_not_recorded():
    order = CommercialOrderState("o2")
    ledger = CommercialLedger()
    c = CommercialTransitionCoordinator(ledger)
    with pytest.raises(ValueError, match="INVALID_TRANSITION"):
        c.transition(order, "COMPLETED", "l1", evidence_refs=("x",))
    assert order.state == "NEW"
    assert ledger.for_order("o2") == []


def test_duplicate_ledger_entry_rolls_back_state():
    order = CommercialOrderState("o3")
    ledger = CommercialLedger()
    c = CommercialTransitionCoordinator(ledger)
    c.transition(order, "PAYMENT_VERIFIED", "l1", evidence_refs=("p1",))
    with pytest.raises(ValueError, match="DUPLICATE_LEDGER_ENTRY"):
        c.transition(order, "REVENUE_REALIZED", "l1", evidence_refs=("r1",))
    assert order.state == "PAYMENT_VERIFIED"
    assert len(ledger.for_order("o3")) == 1
