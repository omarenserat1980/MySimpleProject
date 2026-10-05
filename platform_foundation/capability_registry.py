from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Callable

@dataclass(frozen=True)
class Capability:
    name: str
    owner: str
    version: str
    executor_id: str
    required_capabilities: frozenset[str] = frozenset()
    enabled: bool = True

class CapabilityRegistry:
    """Brain-owned registry for executable capabilities and their authority boundary."""
    def __init__(self):
        self._items: dict[str, Capability] = {}
        self._handlers: dict[str, Callable[..., Any]] = {}

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

    def readiness(self, name: str) -> dict[str, Any]:
        item = self.get(name)
        if item is None:
            return {"ready": False, "reason": "unknown_capability"}
        return {
            "ready": item.enabled and name in self._handlers,
            "capability": asdict(item),
            "reason": "enabled" if item.enabled else "disabled",
        }

    def invoke(self, name: str, **kwargs: Any) -> Any:
        item = self.get(name)
        if item is None:
            raise ValueError(f"unknown_capability:{name}")
        if not item.enabled:
            raise PermissionError(f"capability_disabled:{name}")
        return self._handlers[name](**kwargs)

__all__ = ["Capability", "CapabilityRegistry"]
