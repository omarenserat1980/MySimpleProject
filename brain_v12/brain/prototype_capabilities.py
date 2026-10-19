"""Small, fail-closed prototype adapters for Brain capabilities.

These are contracts/prototypes, not replacements for existing Brain services.
They do not capture Android screens, reserve physical resources, run shell
commands, open network connections, or prove real mining/revenue.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import math
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
    """Logical budget only; units are caller-defined, not physical telemetry."""
    capacity: dict[str, float]
    reserved: dict[str, float] = field(default_factory=dict)

    @staticmethod
    def _finite_number(value: Any) -> bool:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        try:
            return math.isfinite(float(value))
        except (OverflowError, ValueError):
            return False

    def __post_init__(self) -> None:
        if not isinstance(self.capacity, dict) or not isinstance(self.reserved, dict):
            raise ValueError("INVALID_RESOURCE_BUDGET")
        for resource, capacity in self.capacity.items():
            if not isinstance(resource, str) or not resource.strip():
                raise ValueError("INVALID_RESOURCE_NAME")
            if not self._finite_number(capacity) or capacity < 0:
                raise ValueError("INVALID_RESOURCE_CAPACITY")
        for resource, amount in self.reserved.items():
            if resource not in self.capacity:
                raise ValueError("UNKNOWN_RESOURCE")
            if not self._finite_number(amount) or amount < 0:
                raise ValueError("INVALID_RESERVED_RESOURCE_AMOUNT")
            if amount > self.capacity[resource]:
                raise ValueError("RESOURCE_BUDGET_EXCEEDED")

    def reserve(self, resource: str, amount: float) -> None:
        if resource not in self.capacity:
            raise ValueError("UNKNOWN_RESOURCE")
        if not self._finite_number(amount) or amount <= 0:
            raise ValueError("INVALID_RESOURCE_AMOUNT")
        current = self.reserved.get(resource, 0.0)
        total = current + float(amount)
        if not math.isfinite(total):
            raise ValueError("INVALID_RESOURCE_AMOUNT")
        if total > self.capacity[resource]:
            raise ValueError("RESOURCE_BUDGET_EXCEEDED")
        self.reserved[resource] = total

    def release(self, resource: str, amount: float) -> None:
        current = self.reserved.get(resource, 0.0)
        if (
            not self._finite_number(amount)
            or amount <= 0
            or amount > current
        ):
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
        if not isinstance(kind, str) or not kind.strip() or not isinstance(source, str) or not source.strip() or not isinstance(payload, dict):
            raise ValueError("INVALID_EVIDENCE_RECORD")
        if evidence_class not in {"simulated", "local_test", "device_observed", "external"}:
            raise ValueError("INVALID_EVIDENCE_CLASS")
        # Isolate stored evidence from caller-owned nested objects.
        safe_payload = deepcopy(payload)
        previous = self.records[-1]["digest"] if self.records else "GENESIS"
        body = {
            "sequence": len(self.records) + 1,
            "kind": kind,
            "source": source,
            "evidence_class": evidence_class,
            "payload": safe_payload,
            "previous_digest": previous,
        }
        try:
            canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("INVALID_EVIDENCE_PAYLOAD") from exc
        entry = {**body, "digest": hashlib.sha256(canonical.encode("utf-8")).hexdigest()}
        self.records.append(entry)
        return deepcopy(entry)

    def verify_chain(self) -> bool:
        previous = "GENESIS"
        for index, entry in enumerate(self.records, start=1):
            if not isinstance(entry, dict):
                return False
            body = {k: v for k, v in entry.items() if k != "digest"}
            if body.get("sequence") != index or body.get("previous_digest") != previous:
                return False
            try:
                canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
            except (TypeError, ValueError):
                return False
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
        real_path = (
            not t.simulated and t.transport_connected and t.tls_authenticated
            and t.worker_active and t.accepted_shares_reported > 0
            and t.independent_pool_confirmation
        )
        return {
            "status": "REAL_SHARE_EVIDENCE_COMPLETE" if real_path else "NOT_VERIFIED",
            "stop_required": not (t.transport_connected and t.tls_authenticated),
            "simulated": t.simulated,
            "real_mining_verified": bool(real_path),
            "revenue_verified": bool(real_path and t.revenue_confirmed),
            "missing_evidence": [
                name for name, ok in (
                    ("non_simulated_runtime", not t.simulated),
                    ("transport_connected", t.transport_connected),
                    ("tls_authenticated", t.tls_authenticated),
                    ("worker_active", t.worker_active),
                    ("pool_reported_accepted_share", t.accepted_shares_reported > 0),
                    ("independent_pool_confirmation", t.independent_pool_confirmation),
                ) if not ok
            ],
        }
