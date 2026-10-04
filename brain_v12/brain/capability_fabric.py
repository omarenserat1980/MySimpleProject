"""Capability Fabric with runtime-health-aware executor selection."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .health_probe import HealthProbeEngine


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
    """Provider-neutral capability registry with health-gated bounded fallback."""

    def __init__(self, health: HealthProbeEngine | None = None) -> None:
        self._executors: dict[str, ExecutorSpec] = {}
        self.health = health or HealthProbeEngine()

    def register(self, spec: ExecutorSpec, probe: Callable[[], Any] | None = None) -> None:
        if not spec.executor_id or not spec.capability:
            raise ValueError("executor_id and capability are required")
        self._executors[spec.executor_id] = spec
        if probe is not None:
            self.health.register(spec.executor_id, probe)

    def discover(self, capability: str, require_healthy: bool = True) -> list[ExecutorSpec]:
        candidates = [
            x for x in self._executors.values()
            if x.capability == capability and x.state == "ONLINE"
        ]
        if require_healthy:
            candidates = [x for x in candidates if self.health.healthy(x.executor_id)]
        return sorted(candidates, key=lambda x: (x.priority, x.cost_class, x.executor_id))

    def probe_capability(self, capability: str) -> list[dict[str, Any]]:
        for spec in self._executors.values():
            if spec.capability == capability:
                self.health.probe(spec.executor_id)
        return self.health.snapshot()

    def plan(
        self,
        capability: str,
        required_permissions: set[str] | None = None,
        require_healthy: bool = True,
        probe_before_select: bool = False,
    ) -> list[ExecutorSpec]:
        required = required_permissions or set()
        if probe_before_select:
            self.probe_capability(capability)
        return [
            x for x in self.discover(capability, require_healthy=require_healthy)
            if required.issubset(x.permissions)
        ]

    def execute(
        self,
        capability: str,
        runner: Callable[[ExecutorSpec], Any],
        required_permissions: set[str] | None = None,
        max_attempts: int = 3,
        probe_before_select: bool = True,
    ) -> dict[str, Any]:
        candidates = self.plan(
            capability,
            required_permissions,
            require_healthy=True,
            probe_before_select=probe_before_select,
        )
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
                "healthy": self.health.healthy(x.executor_id),
            }
            for x in sorted(self._executors.values(), key=lambda x: x.executor_id)
        ]
