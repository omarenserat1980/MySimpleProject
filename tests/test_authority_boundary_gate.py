import pytest

from platform_foundation.capability_registry import Capability, CapabilityRegistry
from platform_foundation.execution_policy import BrainExecutionPolicy, ExecutorDescriptor


def test_unknown_capability_is_denied():
    registry = CapabilityRegistry()
    with pytest.raises(ValueError, match="unknown_capability"):
        registry.invoke("not-registered")


def test_disabled_capability_is_denied():
    registry = CapabilityRegistry()
    registry.register(
        Capability("disabled", "brain", "1", "brain-local", enabled=False),
        lambda: "must-not-run",
    )
    with pytest.raises(PermissionError, match="capability_disabled"):
        registry.invoke("disabled")


def test_contract_mismatch_is_denied():
    registry = CapabilityRegistry()
    registry.register(
        Capability("bad-contract", "brain", "1", "brain-local", contract="v2"),
        lambda: "must-not-run",
    )
    with pytest.raises(PermissionError, match="contract_mismatch"):
        registry.invoke("bad-contract")


def test_unauthorized_executor_is_denied():
    registry = CapabilityRegistry(policy=BrainExecutionPolicy())
    registry.register(
        Capability("local-only", "brain", "1", "brain-local"),
        lambda: "must-not-run",
    )
    executors = [
        ExecutorDescriptor("github", "external", frozenset()),
    ]
    with pytest.raises(PermissionError, match="executor_not_authorized"):
        registry.invoke("local-only", executors=executors)


def test_required_capability_mismatch_is_denied():
    registry = CapabilityRegistry(policy=BrainExecutionPolicy())
    registry.register(
        Capability("privileged", "brain", "1", "brain-local", required_capabilities=frozenset({"filesystem.write"})),
        lambda: "must-not-run",
    )
    executors = [
        ExecutorDescriptor("brain-local", "brain", frozenset({"filesystem.read"})),
    ]
    with pytest.raises(PermissionError, match="executor_not_authorized"):
        registry.invoke("privileged", executors=executors)


def test_brain_executor_is_allowed():
    registry = CapabilityRegistry(policy=BrainExecutionPolicy())
    registry.register(
        Capability("safe-local", "brain", "1", "brain-local"),
        lambda: "executed",
    )
    executors = [
        ExecutorDescriptor("brain-local", "brain", True, frozenset()),
    ]
    assert registry.invoke("safe-local", executors=executors) == "executed"
