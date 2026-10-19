"""Small, fail-closed prototype adapters for Brain capabilities.

These are contracts/prototypes, not replacements for existing Brain services.
They do not capture Android screens, reserve physical resources, run shell
commands, open network connections, or prove real mining/revenue.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from typing import Any, Callable


class TaskState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    VERIFIED = "verified"
    COMPLETED = "completed"
    FAILED = "failed"


_ALLOWED_TRANSITIONS = {
    TaskState.PENDING: {TaskState.RUNNING, TaskState.FAILED},
    TaskState.RUNNING: {TaskState.VERIFIED, TaskState.FAILED},
    TaskState.VERIFIED: {TaskState.COMPLETED, TaskState.FAILED},
    TaskState.COMPLETED: set(),
    TaskState.FAILED: set(),
}


@dataclass
class TaskOrchestratorPrototype:
    """Minimal task state machine; existing Brain orchestrator remains canonical."""
    states: dict[str, TaskState] = field(default_factory=dict)

    def create(self, task_id: str) -> TaskState:
        if not isinstance(task_id, str) or not task_id.strip() or task_id in self.states:
            raise ValueError("INVALID_OR_DUPLICATE_TASK_ID")
        self.states[task_id] = TaskState.PENDING
        return self.states[task_id]

    def transition(self, task_id: str, new_state: TaskState) -> TaskState:
        if task_id not in self.states:
            raise KeyError("UNKNOWN_TASK")
        if new_state not in _ALLOWED_TRANSITIONS[self.states[task_id]]:
            raise ValueError("INVALID_TASK_STATE_TRANSITION")
        self.states[task_id] = new_state
        return new_state


@dataclass
class ResourceBudgetPrototype:
    """Logical resource budget only; units are caller-defined, not device telemetry."""
    capacity: dict[str, float]
    reserved: dict[str, float] = field(default_factory=dict)

    def reserve(self, resource: str, amount: float) -> None:
        if resource not in self.capacity:
            raise ValueError("UNKNOWN_RESOURCE")
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("INVALID_RESOURCE_AMOUNT")
        current = self.reserved.get(resource, 0.0)
        if current + amount > self.capacity[resource]:
            raise ValueError("RESOURCE_BUDGET_EXCEEDED")
        self.reserved[resource] = current + float(amount)

    def release(self, resource: str, amount: float) -> None:
        current = self.reserved.get(resource, 0.0)
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount <= 0 or amount > current:
            raise ValueError("INVALID_RESOURCE_RELEASE")
        remaining = current - float(amount)
        if remaining:
            self.reserved[resource] = remaining
        else:
            self.reserved.pop(resource, None)


@dataclass
class EvidenceEnginePrototype:
    """Hash-linked in-memory evidence; not durable or independent evidence."""
    records: list[dict[str, Any]] = field(default_factory=list)

    def record(self, *, kind: str, source: str, payload: dict[str, Any],
               evidence_class: str = "simulated") -> dict[str, Any]:
        if not kind or not source or not isinstance(payload, dict):
            raise ValueError("INVALID_EVIDENCE_RECORD")
        if evidence_class not in {"simulated", "local_test", "device_observed", "external"}:
            raise ValueError("INVALID_EVIDENCE_CLASS")
        previous = self.records[-1]["digest"] if self.records else "GENESIS"
        body = {
            "sequence": len(self.records) + 1,
            "kind": kind,
            "source": source,
            "evidence_class": evidence_class,
            "payload": payload,
            "previous_digest": previous,
        }
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        entry = {**body, "digest": hashlib.sha256(canonical.encode("utf-8")).hexdigest()}
        self.records.append(entry)
        return dict(entry)

    def verify_chain(self) -> bool:
        previous = "GENESIS"
        for index, entry in enumerate(self.records, start=1):
            body = {k: v for k, v in entry.items() if k != "digest"}
            if body.get("sequence") != index or body.get("previous_digest") != previous:
                return False
            canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            if digest != entry.get("digest"):
                return False
            previous = digest
        return True


@dataclass(frozen=True)
class VisualObservation:
    """Caller-supplied observation; this type does not itself read a screen."""
    state: str
    confidence: float
    source: str = "provided_observation"


class VisualAgentPrototype:
    """Normalize supplied observations and reject uncertain/invalid readings."""
    @staticmethod
    def assess(observation: VisualObservation, *, minimum_confidence: float = 0.9) -> dict[str, Any]:
        if not isinstance(observation.state, str) or not observation.state.strip():
            raise ValueError("OBSERVATION_STATE_REQUIRED")
        if not 0.0 <= observation.confidence <= 1.0:
            raise ValueError("INVALID_OBSERVATION_CONFIDENCE")
        verified = observation.confidence >= minimum_confidence
        return {
            "observed_state": observation.state,
            "confidence": observation.confidence,
            "source": observation.source,
            "decision": "ACCEPT_OBSERVATION" if verified else "STOP_FOR_REVIEW",
            "screen_capture_performed": False,
            "device_state_independently_verified": False,
        }


@dataclass
class RecoveryManagerPrototype:
    """Bounded retry wrapper; never retries after success and never loops forever."""
    max_attempts: int = 2

    def run(self, operation: Callable[[], Any], *, verify: Callable[[Any], bool]) -> dict[str, Any]:
        if isinstance(self.max_attempts, bool) or not isinstance(self.max_attempts, int) or not 1 <= self.max_attempts <= 5:
            raise ValueError("RETRY_BOUND_MUST_BE_1_TO_5")
        errors: list[str] = []
        for attempt in range(1, self.max_attempts + 1):
            try:
                result = operation()
                if verify(result):
                    return {"status": "VERIFIED", "attempts": attempt, "result": result, "errors": errors}
                errors.append("POSTCONDITION_FAILED")
            except Exception as exc:
                errors.append(type(exc).__name__)
        return {"status": "FAILED", "attempts": self.max_attempts, "errors": errors}


@dataclass(frozen=True)
class MiningTelemetry:
    simulated: bool = True
    transport_connected: bool = False
    tls_authenticated: bool = False
    worker_active: bool = False
    accepted_shares_reported: int = 0
    independent_pool_confirmation: bool = False
    revenue_confirmed: bool = False


class MiningSupervisorPrototype:
    """Evidence gate for mining claims; telemetry is input, never fabricated."""
    @staticmethod
    def assess(t: MiningTelemetry) -> dict[str, Any]:
        if t.accepted_shares_reported < 0:
            raise ValueError("INVALID_SHARE_COUNTER")
        # This prototype receives caller-supplied booleans, not signed evidence
        # from a trusted server-side pool collector. Therefore it must never
        # promote telemetry to a real-mining or revenue claim, even when every
        # field is set to a success-looking value.
        observed_conditions = (
            ("non_simulated_runtime", not t.simulated),
            ("transport_connected", t.transport_connected),
            ("tls_authenticated", t.tls_authenticated),
            ("worker_active", t.worker_active),
            ("pool_reported_accepted_share", t.accepted_shares_reported > 0),
            ("independent_pool_confirmation", t.independent_pool_confirmation),
        )
        missing = [name for name, ok in observed_conditions if not ok]
        missing.append("trusted_server_side_evidence_verifier_not_bound")
        return {
            "status": "NOT_VERIFIED",
            "stop_required": not (t.transport_connected and t.tls_authenticated),
            "simulated": t.simulated,
            "real_mining_verified": False,
            "revenue_verified": False,
            "missing_evidence": missing,
            "verification_boundary": (
                "Caller-supplied telemetry is not proof; a trusted server-side "
                "collector and verifier must be integrated before this prototype "
                "can certify live mining or revenue."
            ),
        }
