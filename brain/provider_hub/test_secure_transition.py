import pytest

from brain.provider_hub.commercial_ledger import CommercialLedger
from brain.provider_hub.commercial_state import CommercialOrderState
from brain.provider_hub.integrity_chain import IntegrityChain
from brain.provider_hub.secure_transition import SecureCommercialTransitionCoordinator


def test_transition_writes_ledger_and_integrity():
    order = CommercialOrderState("o1")
    ledger = CommercialLedger()
    integrity = IntegrityChain()
    c = SecureCommercialTransitionCoordinator(ledger, integrity)
    result = c.transition(order, "PAYMENT_VERIFIED", "e1", evidence_refs=("p1",))
    assert result.state == "PAYMENT_VERIFIED"
    assert len(ledger.for_order("o1")) == 1
    assert integrity.verify() is True
    assert result.integrity_hash == integrity.entries()[0].entry_hash


def test_integrity_failure_rolls_back_state():
    order = CommercialOrderState("o2")
    ledger = CommercialLedger()
    integrity = IntegrityChain()
    c = SecureCommercialTransitionCoordinator(ledger, integrity)
    c.transition(order, "PAYMENT_VERIFIED", "e1", evidence_refs=("p1",))

    with pytest.raises(ValueError, match="DUPLICATE"):
        c.transition(order, "REVENUE_REALIZED", "e1", evidence_refs=("r1",))

    assert order.state == "PAYMENT_VERIFIED"
    assert len(ledger.for_order("o2")) == 1
    assert len(integrity.entries()) == 1
