import pytest

from brain.provider_hub.containment import CommercialContainmentGate


def test_containment_blocks_sensitive_operations():
    gate = CommercialContainmentGate()
    gate.contain("i1", "o1", "INTEGRITY_CHAIN_INVALID")
    assert gate.is_contained("o1") is True
    with pytest.raises(RuntimeError, match="COMMERCIAL_ORDER_CONTAINED:o1"):
        gate.assert_clear("o1")


def test_release_restores_access():
    gate = CommercialContainmentGate()
    gate.contain("i1", "o1", "STATE_LEDGER_MISMATCH")
    gate.release("i1")
    assert gate.is_contained("o1") is False
    gate.assert_clear("o1")


def test_duplicate_incident_is_rejected():
    gate = CommercialContainmentGate()
    gate.contain("i1", "o1", "test")
    with pytest.raises(ValueError, match="DUPLICATE_INCIDENT:i1"):
        gate.contain("i1", "o1", "test")
