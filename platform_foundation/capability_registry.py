from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Callable

from .execution_policy import BrainExecutionPolicy, ExecutorDescriptor, ExecutorDecision

@dataclass(frozen=True)
class Capability:
    name: str
    owner: str
    version: str
    executor_id: str
    required_capabilities: frozenset[str] = frozenset()
    enabled: bool = True
    contract: str = "v1"

class CapabilityRegistry:
    """Brain-owned registry for executable capabilities and their authority boundary."""
    def __init__(self, policy: BrainExecutionPolicy | None = None):
        self._items: dict[str, Capability] = {}
        self._handlers: dict[str, Callable[..., Any]] = {}
        self.policy = policy or BrainExecutionPolicy()

    def register(self, capability: Capability, handler: Callable[..., Any]) -> None:
        if not capability.name or not capability.owner or not capability.executor_id:
            raise ValueError("invalid capability identity")
        if capability.owner.strip().lower() != "brain":
            raise ValueError("capability owner must be brain")
        if not callable(handler):
            raise ValueError("capability handler required")
        if capability.name in self._items:
            raise ValueError(f"capability_already_registered:{capability.name}")
        self._items[capability.name] = capability
        self._handlers[capability.name] = handler

    def get(self, name: str) -> Capability | None:
        return self._items.get(name)

    def list(self) -> list[Capability]:
        return list(self._items.values())

    def readiness(self, name: str, *, expected_contract: str = "v1") -> dict[str, Any]:
        item = self.get(name)
        if item is None:
            return {"ready": False, "reason": "unknown_capability"}
        if not item.enabled:
            return {"ready": False, "capability": asdict(item), "reason": "disabled"}
        if item.contract != expected_contract:
            return {"ready": False, "capability": asdict(item), "reason": "contract_mismatch"}
        if name not in self._handlers:
            return {"ready": False, "capability": asdict(item), "reason": "handler_missing"}
        return {"ready": True, "capability": asdict(item), "reason": "ready"}

    def authorize_executor(self, name: str, executors: list[ExecutorDescriptor]) -> dict[str, Any]:
        item = self.get(name)
        if item is None:
            return {"allowed": False, "reason": "unknown_capability"}
        decision = self.policy.select([e for e in executors if e.executor_id == item.executor_id], required_capabilities=set(item.required_capabilities))
        return {"allowed": decision.decision is ExecutorDecision.ALLOWED, "executor_id": decision.executor_id, "reason": decision.reason}

    def invoke(self, name: str, *, executors: list[ExecutorDescriptor] | None = None, **kwargs: Any) -> Any:
        item = self.get(name)
        if item is None:
            raise ValueError(f"unknown_capability:{name}")
        if not item.enabled:
            raise PermissionError(f"capability_disabled:{name}")
        if executors is not None:
            authorization = self.authorize_executor(name, executors)
            if not authorization["allowed"]:
                raise PermissionError(f"executor_not_authorized:{name}:{authorization['reason']}")
        return self._handlers[name](**kwargs)

__all__ = ["Capability", "CapabilityRegistry"]
