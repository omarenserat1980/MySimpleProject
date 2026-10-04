"""Brain Capability Fabric.

Brain plans against capabilities, not against a single application or vendor.
Executors are registered with health, priority, cost, and permission metadata.
Selection is deterministic and returns ordered fallbacks; execution itself is
kept behind an explicit executor callback so the fabric stays provider-neutral.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class ExecutorSpec:
    executor_id: str
    capability: str
    priority: int = 100
    state: str = "ONLINE"
    cost_class: str = "FREE"
    permissions: frozenset[str] = frozenset()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionAttempt:
    executor_id: str
    ok: bool
    result: Any = None
    error: str | None = None


class CapabilityFabric:
    """Provider-neutral capability registry and bounded fallback selector."""

    def __init__(self) -> None:
        self._executors: dict[str, ExecutorSpec] = {}

    def register(self, spec: ExecutorSpec) -> None:
        if not spec.executor_id or not spec.capability:
            raise ValueError("executor_id and capability are required")
        self._executors[spec.executor_id] = spec

    def discover(self, capability: str) -> list[ExecutorSpec]:
        return sorted(
            (
                x for x in self._executors.values()
                if x.capability == capability and x.state == "ONLINE"
            ),
            key=lambda x: (x.priority, x.cost_class, x.executor_id),
        )

    def plan(self, capability: str, required_permissions: set[str] | None = None) -> list[ExecutorSpec]:
        required = required_permissions or set()
        return [
            x for x in self.discover(capability)
            if required.issubset(x.permissions)
        ]

    def execute(
        self,
        capability: str,
        runner: Callable[[ExecutorSpec], Any],
        required_permissions: set[str] | None = None,
        max_attempts: int = 3,
    ) -> dict[str, Any]:
        candidates = self.plan(capability, required_permissions)
        attempts: list[ExecutionAttempt] = []
        for spec in candidates[:max(0, max_attempts)]:
            try:
                result = runner(spec)
                attempts.append(ExecutionAttempt(spec.executor_id, True, result=result))
                return {
                    "status": "SUCCESS",
                    "capability": capability,
                    "executor_id": spec.executor_id,
                    "attempts": [a.__dict__ for a in attempts],
                }
            except Exception as exc:
                attempts.append(ExecutionAttempt(spec.executor_id, False, error=str(exc)))

        return {
            "status": "FAILED",
            "capability": capability,
            "executor_id": None,
            "attempts": [a.__dict__ for a in attempts],
        }

    def snapshot(self) -> list[dict[str, Any]]:
        return [
            {
                "executor_id": x.executor_id,
                "capability": x.capability,
                "priority": x.priority,
                "state": x.state,
                "cost_class": x.cost_class,
                "permissions": sorted(x.permissions),
                "metadata": dict(x.metadata),
            }
            for x in sorted(self._executors.values(), key=lambda x: x.executor_id)
        ]
