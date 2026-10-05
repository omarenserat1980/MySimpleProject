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


def test_capability_requires_authorized_brain_executor():
    from platform_foundation.execution_policy import ExecutorDescriptor
    registry = CapabilityRegistry()
    registry.register(
        Capability("python", "brain", "1.0", "brain-local-01", frozenset({"python"})),
        lambda: "ok",
    )
    allowed = [ExecutorDescriptor("brain-local-01", "brain", True, frozenset({"python"}))]
    assert registry.authorize_executor("python", allowed)["allowed"]
    assert registry.invoke("python", executors=allowed) == "ok"


def test_external_executor_cannot_authorize_brain_capability():
    from platform_foundation.execution_policy import ExecutorDescriptor
    registry = CapabilityRegistry()
    registry.register(Capability("python", "brain", "1.0", "github-hosted", frozenset({"python"})), lambda: "bad")
    external = [ExecutorDescriptor("github-hosted", "github", False, frozenset({"python"}))]
    assert not registry.authorize_executor("python", external)["allowed"]
    import pytest
    with pytest.raises(PermissionError):
        registry.invoke("python", executors=external)
