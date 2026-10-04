from dataclasses import replace

from brain.provider_hub.integrity_chain import IntegrityChain


def test_chain_is_valid_after_append():
    chain = IntegrityChain()
    chain.append("e1", "o1", "NEW", "PAYMENT_VERIFIED", ("p1",))
    chain.append("e2", "o1", "PAYMENT_VERIFIED", "REVENUE_REALIZED", ("r1",))
    assert chain.verify() is True


def test_tampering_is_detected():
    chain = IntegrityChain()
    chain.append("e1", "o1", "NEW", "PAYMENT_VERIFIED", ("p1",))
    chain.append("e2", "o1", "PAYMENT_VERIFIED", "REVENUE_REALIZED", ("r1",))
    original = chain.entries()[1]
    chain._entries[1] = replace(original, to_state="COMPLETED")
    assert chain.verify() is False


def test_duplicate_entry_is_rejected():
    chain = IntegrityChain()
    chain.append("e1", "o1", "NEW", "PAYMENT_VERIFIED")
    try:
        chain.append("e1", "o1", "NEW", "PAYMENT_VERIFIED")
    except ValueError as exc:
        assert str(exc) == "DUPLICATE_INTEGRITY_ENTRY:e1"
    else:
        raise AssertionError("duplicate integrity entry accepted")
