import pytest
from platform_foundation.capability_registry import Capability, CapabilityRegistry

def test_brain_owned_capability_registers_and_invokes():
    registry = CapabilityRegistry()
    registry.register(
        Capability("verification", "brain", "1.0", "brain-local-01"),
        lambda value: {"verified": value},
    )
    assert registry.readiness("verification")["ready"]
    assert registry.invoke("verification", value=True) == {"verified": True}

def test_external_owner_is_rejected():
    registry = CapabilityRegistry()
    with pytest.raises(ValueError, match="owner must be brain"):
        registry.register(Capability("x", "github", "1.0", "github-hosted"), lambda: None)

def test_disabled_capability_cannot_execute():
    registry = CapabilityRegistry()
    registry.register(
        Capability("x", "brain", "1.0", "brain-local-01", enabled=False),
        lambda: "bad",
    )
    assert not registry.readiness("x")["ready"]
    with pytest.raises(PermissionError):
        registry.invoke("x")
