"""Policy primitives for Brain multi-agent collaboration.

This module is deliberately a control-plane building block, not a second
orchestrator and not a model/provider executor. It is dependency-free and can
be exercised offline before wiring it into BrainSupervisor.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from hashlib import sha256
import json
import time
from typing import Any, Iterable


class AgentRole(str, Enum):
    COORDINATOR = "coordinator"
    PLANNER = "planner"
    IMPLEMENTER = "implementer"
    REVIEWER = "reviewer"
    VERIFIER = "verifier"


class CollaborationState(str, Enum):
    CREATED = "CREATED"
    PLANNED = "PLANNED"
    READY = "READY"
    RUNNING = "RUNNING"
    REVIEW_PENDING = "REVIEW_PENDING"
    VERIFYING = "VERIFYING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


_TERMINAL = {
    CollaborationState.ACCEPTED,
    CollaborationState.REJECTED,
    CollaborationState.BLOCKED,
    CollaborationState.CANCELLED,
    CollaborationState.FAILED,
    CollaborationState.EXPIRED,
}
_ALLOWED_TRANSITIONS = {
    CollaborationState.CREATED: {CollaborationState.PLANNED, CollaborationState.BLOCKED, CollaborationState.CANCELLED},
    CollaborationState.PLANNED: {CollaborationState.READY, CollaborationState.BLOCKED, CollaborationState.CANCELLED},
    CollaborationState.READY: {CollaborationState.RUNNING, CollaborationState.BLOCKED, CollaborationState.CANCELLED},
    CollaborationState.RUNNING: {CollaborationState.REVIEW_PENDING, CollaborationState.FAILED, CollaborationState.BLOCKED, CollaborationState.CANCELLED, CollaborationState.EXPIRED},
    CollaborationState.REVIEW_PENDING: {CollaborationState.VERIFYING, CollaborationState.REJECTED, CollaborationState.BLOCKED},
    CollaborationState.VERIFYING: {CollaborationState.ACCEPTED, CollaborationState.REJECTED, CollaborationState.BLOCKED},
}
_WRITE_ROLES = {AgentRole.IMPLEMENTER}


@dataclass(frozen=True)
class TaskEnvelope:
    task_id: str
    objective: str
    role: AgentRole
    repository: str
    branch: str
    base_commit: str
    allowed_paths: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    idempotency_key: str
    max_attempts: int = 3
    deadline_epoch: float = 0.0
    dependencies: tuple[str, ...] = ()
    forbidden_actions: tuple[str, ...] = (
        "write_main", "force_push", "merge", "deploy", "publish_external", "secrets_admin",
    )

    def validate(self) -> None:
        required = {
            "task_id": self.task_id,
            "objective": self.objective,
            "repository": self.repository,
            "branch": self.branch,
            "base_commit": self.base_commit,
            "idempotency_key": self.idempotency_key,
        }
        missing = [name for name, value in required.items() if not isinstance(value, str) or not value.strip()]
        if missing:
            raise ValueError("missing_required_fields:" + ",".join(missing))
        if not isinstance(self.role, AgentRole):
            raise ValueError("unknown_agent_role")
        if not self.allowed_paths or any(not p.strip() or p.startswith("/") or ".." in p.split("/") for p in self.allowed_paths):
            raise ValueError("invalid_allowed_paths")
        if not self.acceptance_criteria or any(not c.strip() for c in self.acceptance_criteria):
            raise ValueError("acceptance_criteria_required")
        if not 1 <= int(self.max_attempts) <= 5:
            raise ValueError("max_attempts_out_of_range")
        if self.deadline_epoch and self.deadline_epoch <= time.time():
            raise ValueError("task_deadline_expired")
        if self.branch in {"main", "master"}:
            raise ValueError("protected_base_branch_cannot_be_task_branch")


@dataclass(frozen=True)
class EvidenceRecord:
    task_id: str
    attempt_id: str
    tested_commit: str
    kind: str
    payload: dict[str, Any]
    payload_sha256: str
    created_at: float

    @classmethod
    def create(
        cls, *, task_id: str, attempt_id: str, tested_commit: str,
        kind: str, payload: dict[str, Any],
    ) -> "EvidenceRecord":
        if not all(isinstance(v, str) and v.strip() for v in (task_id, attempt_id, tested_commit, kind)):
            raise ValueError("evidence_identity_required")
        if not isinstance(payload, dict) or not payload:
            raise ValueError("evidence_payload_required")
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")
        return cls(task_id, attempt_id, tested_commit, kind, payload, sha256(encoded).hexdigest(), time.time())


@dataclass
class CollaborationTask:
    envelope: TaskEnvelope
    state: CollaborationState = CollaborationState.CREATED
    attempt: int = 0
    implementer_id: str | None = None
    reviewer_id: str | None = None
    head_commit: str | None = None
    criteria_results: dict[str, bool] = field(default_factory=dict)
    evidence: list[EvidenceRecord] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)

    def transition(self, target: CollaborationState, *, actor: str, reason: str) -> None:
        if self.state in _TERMINAL:
            raise ValueError("terminal_task_cannot_transition")
        if target not in _ALLOWED_TRANSITIONS.get(self.state, set()):
            raise ValueError(f"invalid_collaboration_transition:{self.state.value}->{target.value}")
        self.events.append({
            "ts": time.time(), "from": self.state.value, "to": target.value,
            "actor": actor, "reason": reason,
        })
        self.state = target


class CollaborationCoordinator:
    """Small policy layer for validating role work and evidence."""

    def __init__(self) -> None:
        self.tasks: dict[str, CollaborationTask] = {}
        self._idempotency: dict[str, str] = {}
        self._path_owners: dict[str, str] = {}

    def create_task(self, envelope: TaskEnvelope) -> CollaborationTask:
        envelope.validate()
        if envelope.task_id in self.tasks:
            raise ValueError("duplicate_task_id")
        prior = self._idempotency.get(envelope.idempotency_key)
        if prior:
            raise ValueError("duplicate_idempotency_key:" + prior)
        task = CollaborationTask(envelope=envelope)
        task.events.append({"ts": time.time(), "event": "task_created", "actor": "coordinator"})
        self.tasks[envelope.task_id] = task
        self._idempotency[envelope.idempotency_key] = envelope.task_id
        return task

    def mark_planned(self, task_id: str, *, planner_id: str) -> CollaborationTask:
        task = self._get(task_id)
        task.transition(CollaborationState.PLANNED, actor=planner_id, reason="structured_plan_recorded")
        return task

    def mark_ready(self, task_id: str, *, coordinator_id: str = "coordinator") -> CollaborationTask:
        task = self._get(task_id)
        task.transition(CollaborationState.READY, actor=coordinator_id, reason="plan_and_dependencies_checked")
        return task

    def reserve_paths(self, task_id: str, paths: Iterable[str]) -> None:
        """Reserve normalized exact paths; overlapping ownership fails closed."""
        self._get(task_id)
        normalized = tuple(dict.fromkeys(str(p).strip().strip("/") for p in paths))
        if not normalized or any(not p or ".." in p.split("/") for p in normalized):
            raise ValueError("invalid_reserved_paths")
        for path in normalized:
            for existing, owner in self._path_owners.items():
                overlaps = path == existing or path.startswith(existing + "/") or existing.startswith(path + "/")
                if overlaps and owner != task_id:
                    raise ValueError("path_write_conflict:" + path + ":" + owner)
        for path in normalized:
            self._path_owners[path] = task_id

    @staticmethod
    def authorize_path(role: AgentRole, path: str, allowed_paths: Iterable[str]) -> bool:
        if role not in _WRITE_ROLES or not isinstance(path, str) or not path.strip():
            return False
        if path.startswith("/") or ".." in path.split("/"):
            return False
        return any(path == prefix or path.startswith(prefix.rstrip("/") + "/") for prefix in allowed_paths)

    def start_implementation(self, task_id: str, *, implementer_id: str, head_commit: str) -> CollaborationTask:
        task = self._get(task_id)
        if task.state != CollaborationState.READY:
            raise ValueError("task_not_ready")
        if task.envelope.role != AgentRole.IMPLEMENTER:
            raise ValueError("task_role_not_implementer")
        if not implementer_id.strip() or not head_commit.strip():
            raise ValueError("implementer_and_head_commit_required")
        if head_commit != task.envelope.base_commit:
            raise ValueError("stale_base_commit")
        task.implementer_id = implementer_id
        task.head_commit = head_commit
        task.attempt += 1
        if task.attempt > task.envelope.max_attempts:
            raise ValueError("attempt_limit_reached")
        task.transition(CollaborationState.RUNNING, actor=implementer_id, reason="implementation_started")
        return task

    def submit_for_review(self, task_id: str, *, implementer_id: str, head_commit: str) -> CollaborationTask:
        task = self._get(task_id)
        if task.state != CollaborationState.RUNNING:
            raise ValueError("task_not_running")
        if implementer_id != task.implementer_id:
            raise ValueError("implementer_identity_mismatch")
        if not head_commit.strip():
            raise ValueError("head_commit_required")
        task.head_commit = head_commit
        task.transition(CollaborationState.REVIEW_PENDING, actor=implementer_id, reason="patch_submitted")
        return task

    def record_review(self, task_id: str, *, reviewer_id: str, approved: bool) -> CollaborationTask:
        task = self._get(task_id)
        if task.state != CollaborationState.REVIEW_PENDING:
            raise ValueError("task_not_pending_review")
        if not reviewer_id.strip() or reviewer_id == task.implementer_id:
            raise ValueError("reviewer_must_be_independent")
        task.reviewer_id = reviewer_id
        if not approved:
            task.transition(CollaborationState.REJECTED, actor=reviewer_id, reason="review_rejected")
            return task
        task.transition(CollaborationState.VERIFYING, actor=reviewer_id, reason="independent_review_approved")
        return task

    def add_evidence(self, task_id: str, evidence: EvidenceRecord) -> CollaborationTask:
        task = self._get(task_id)
        if evidence.task_id != task_id:
            raise ValueError("evidence_task_mismatch")
        if task.state != CollaborationState.VERIFYING:
            raise ValueError("task_not_verifying")
        if evidence.tested_commit != task.head_commit:
            raise ValueError("evidence_commit_mismatch")
        if evidence.attempt_id != f"{task_id}:{task.attempt}":
            raise ValueError("evidence_attempt_mismatch")
        task.evidence.append(evidence)
        return task

    def finalize(
        self, task_id: str, *, criteria_results: dict[str, bool],
        required_evidence_kinds: Iterable[str], actor: str = "brain-verification-gate",
    ) -> CollaborationTask:
        task = self._get(task_id)
        if task.state != CollaborationState.VERIFYING:
            raise ValueError("task_not_verifying")
        expected = set(task.envelope.acceptance_criteria)
        if set(criteria_results) != expected or not all(v is True for v in criteria_results.values()):
            task.criteria_results = dict(criteria_results)
            task.transition(CollaborationState.BLOCKED, actor=actor, reason="acceptance_criteria_failed_or_missing")
            return task
        required = set(required_evidence_kinds)
        valid_kinds = {e.kind for e in task.evidence if e.tested_commit == task.head_commit and e.payload}
        if not required or not required.issubset(valid_kinds):
            task.criteria_results = dict(criteria_results)
            task.transition(CollaborationState.BLOCKED, actor=actor, reason="required_evidence_missing")
            return task
        task.criteria_results = dict(criteria_results)
        task.transition(CollaborationState.ACCEPTED, actor=actor, reason="criteria_and_commit_bound_evidence_verified")
        return task

    def export_record(self, task_id: str) -> dict[str, Any]:
        task = self._get(task_id)
        return {
            "schema_version": "1.0",
            "task_id": task.envelope.task_id,
            "repository": task.envelope.repository,
            "branch": task.envelope.branch,
            "base_commit": task.envelope.base_commit,
            "head_commit": task.head_commit,
            "role": task.envelope.role.value,
            "state": task.state.value,
            "attempt": task.attempt,
            "implementer_id": task.implementer_id,
            "reviewer_id": task.reviewer_id,
            "criteria_results": task.criteria_results,
            "evidence": [asdict(item) for item in task.evidence],
            "events": list(task.events),
        }

    def _get(self, task_id: str) -> CollaborationTask:
        try:
            return self.tasks[task_id]
        except KeyError as exc:
            raise ValueError("unknown_task_id") from exc
