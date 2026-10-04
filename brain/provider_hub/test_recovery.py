import pytest

from brain.provider_hub.audit import ProviderAuditLog
from brain.provider_hub.containment import CommercialContainmentGate
from brain.provider_hub.recovery import CommercialRecoveryGate


def test_recovery_requires_verification():
    containment = CommercialContainmentGate()
    audit = ProviderAuditLog()
    containment.contain("i1", "o1", "INTEGRITY_CHAIN_INVALID")
    result = CommercialRecoveryGate(containment, audit).recover("i1", "o1", lambda: False)
    assert result.recovered is False
    assert containment.is_contained("o1") is True
    assert audit.events_for("o1")[0].event_type == "RECOVERY_BLOCKED"


def test_verified_recovery_releases_order():
    containment = CommercialContainmentGate()
    audit = ProviderAuditLog()
    containment.contain("i1", "o1", "STATE_LEDGER_MISMATCH")
    result = CommercialRecoveryGate(containment, audit).recover("i1", "o1", lambda: True)
    assert result.recovered is True
    assert containment.is_contained("o1") is False
    assert audit.events_for("o1")[0].event_type == "RECOVERY_VERIFIED"


def test_unknown_incident_cannot_be_recovered():
    containment = CommercialContainmentGate()
    audit = ProviderAuditLog()
    result = CommercialRecoveryGate(containment, audit).recover("missing", "o1", lambda: True)
    assert result.reason == "ACTIVE_INCIDENT_NOT_FOUND"
