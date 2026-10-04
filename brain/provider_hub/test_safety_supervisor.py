from brain.provider_hub.audit import ProviderAuditLog
from brain.provider_hub.commercial_ledger import CommercialLedger
from brain.provider_hub.commercial_state import CommercialOrderState
from brain.provider_hub.containment import CommercialContainmentGate
from brain.provider_hub.evidence import CommercialEvidenceGate
from brain.provider_hub.integrity_chain import IntegrityChain
from brain.provider_hub.safety_supervisor import CommercialSafetySupervisor


def make():
    ledger = CommercialLedger()
    integrity = IntegrityChain()
    evidence = CommercialEvidenceGate()
    containment = CommercialContainmentGate()
    audit = ProviderAuditLog()
    return CommercialSafetySupervisor(ledger, integrity, evidence, containment, audit), containment


def test_consistent_order_is_allowed():
    supervisor, containment = make()
    order = CommercialOrderState("o1")
    result = supervisor.inspect(order, "i1")
    assert result.safe is True
    assert result.action == "ALLOW"
    assert containment.is_contained("o1") is False


def test_inconsistent_order_is_contained():
    supervisor, containment = make()
    order = CommercialOrderState("o2", "PAYMENT_VERIFIED")
    result = supervisor.inspect(order, "i2")
    assert result.safe is False
    assert result.action == "CONTAIN"
    assert containment.is_contained("o2") is True


def test_recovery_requires_verifier():
    supervisor, containment = make()
    order = CommercialOrderState("o3", "PAYMENT_VERIFIED")
    supervisor.inspect(order, "i3")
    blocked = supervisor.recover_if_verified(order, "i3", lambda: False)
    assert blocked.safe is False
    assert containment.is_contained("o3") is True
    recovered = supervisor.recover_if_verified(order, "i3", lambda: True)
    assert recovered.safe is True
    assert containment.is_contained("o3") is False
