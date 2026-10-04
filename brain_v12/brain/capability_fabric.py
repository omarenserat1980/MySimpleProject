"""Capability Fabric with health, policy verification, and master gate."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .execution_verifier import ExecutionVerifier, evidence_dict
from .health_probe import HealthProbeEngine
from .master_verification_gate import MasterVerificationGate
from .verification_policies import verify_capability


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
    """Provider-neutral capability registry with mandatory Brain-wide verification."""

    def __init__(self, health: HealthProbeEngine | None = None,
                 verifier: ExecutionVerifier | None = None,
                 master_gate: MasterVerificationGate | None = None) -> None:
        self._executors: dict[str, ExecutorSpec] = {}
        self.health = health or HealthProbeEngine()
        self.verifier = verifier or ExecutionVerifier()
        self.master_gate = master_gate or MasterVerificationGate(self.verifier)

    def register(self, spec: ExecutorSpec, probe: Callable[[], Any] | None = None) -> None:
        if not spec.executor_id or not spec.capability:
            raise ValueError("executor_id and capability are required")
        self._executors[spec.executor_id] = spec
        if probe is not None:
            self.health.register(spec.executor_id, probe)

    def discover(self, capability: str, require_healthy: bool = True) -> list[ExecutorSpec]:
        candidates = [x for x in self._executors.values()
                      if x.capability == capability and x.state == "ONLINE"]
        if require_healthy:
            candidates = [x for x in candidates if self.health.healthy(x.executor_id)]
        return sorted(candidates, key=lambda x: (
            -self.health.score(x.executor_id), x.priority, x.cost_class, x.executor_id))

    def plan(self, capability: str, required_permissions: set[str] | None = None,
             require_healthy: bool = True, probe_before_select: bool = False) -> list[ExecutorSpec]:
        if probe_before_select:
            self.probe_capability(capability)
        required = required_permissions or set()
        return [x for x in self.discover(capability, require_healthy)
                if required.issubset(x.permissions)]

    def probe_capability(self, capability: str) -> list[dict[str, Any]]:
        for spec in self._executors.values():
            if spec.capability == capability:
                self.health.probe(spec.executor_id)
        return self.health.snapshot()

    def execute(self, capability: str, runner: Callable[[ExecutorSpec], Any],
                required_permissions: set[str] | None = None, max_attempts: int = 3,
                probe_before_select: bool = True) -> dict[str, Any]:
        candidates = self.plan(capability, required_permissions, True, probe_before_select)
        attempts: list[ExecutionAttempt] = []
        evidence: list[dict[str, Any]] = []
        for spec in candidates[:max(0, max_attempts)]:
            try:
                result = runner(spec)
            except Exception as exc:
                self.health.record_execution(spec.executor_id, False)
                attempts.append(ExecutionAttempt(spec.executor_id, False, error=str(exc)))
                continue

            # Policy is evaluated first; only policy-approved output reaches the
            # master gate. This prevents a custom verifier from accidentally
            # bypassing Brain-wide conservative rules.
            policy = verify_capability(capability, result)
            if not policy.get("verified", False):
                self.health.record_execution(spec.executor_id, False)
                evidence.append({**policy, "executor_id": spec.executor_id})
                attempts.append(ExecutionAttempt(spec.executor_id, False,
                                                 result=result, error="POLICY_REJECTED"))
                continue

            ev = self.verifier.verify(capability, spec.executor_id, result)
            evidence.append(evidence_dict(ev))
            if not ev.verified:
                self.health.record_execution(spec.executor_id, False)
                attempts.append(ExecutionAttempt(spec.executor_id, False,
                                                 result=result, error="VERIFICATION_FAILED"))
                continue

            gate = self.master_gate.evaluate(capability, spec.executor_id, result)
            if gate.verified:
                self.health.record_execution(spec.executor_id, True)
                attempts.append(ExecutionAttempt(spec.executor_id, True, result=result))
                return {"status": gate.status, "capability": capability,
                        "executor_id": spec.executor_id, "result": result,
                        "attempts": [a.__dict__ for a in attempts],
                        "evidence": evidence, "gate": gate.evidence}

            self.health.record_execution(spec.executor_id, False)
            attempts.append(ExecutionAttempt(spec.executor_id, False,
                                             result=result, error="MASTER_GATE_REJECTED"))

        return {"status": "FAILED", "capability": capability, "executor_id": None,
                "attempts": [a.__dict__ for a in attempts], "evidence": evidence}
