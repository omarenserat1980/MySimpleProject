from __future__ import annotations

"""Brain Golden Closed Loop.

One bounded orchestrator owns the complete lifecycle:
INTENT -> PLAN -> AUTHORITY -> ADMIT -> EXECUTE -> OBSERVE -> VERIFY ->
COMMIT -> LEARN -> CLOSE.

Failures enter RECOVER, then either retry the same fenced attempt or CLOSE_FAILED.
Every transition is durable evidence. No phase may grant authority to another.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
import hashlib
import json
import time
from uuid import uuid4


class GoldenPhase(str, Enum):
    INTENT = "INTENT"
    PLAN = "PLAN"
    AUTHORITY = "AUTHORITY"
    ADMIT = "ADMIT"
    EXECUTE = "EXECUTE"
    OBSERVE = "OBSERVE"
    VERIFY = "VERIFY"
    COMMIT = "COMMIT"
    LEARN = "LEARN"
    RECOVER = "RECOVER"
    CLOSED = "CLOSED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class GoldenTask:
    task_id: str
    action: str
    parameters: dict[str, Any] = field(default_factory=dict)
    max_attempts: int = 2


@dataclass
class GoldenState:
    mission_id: str
    task_id: str
    attempt: int = 0
    phase: GoldenPhase = GoldenPhase.INTENT
    status: str = "OPEN"
    execution_key: str = ""
    evidence_ids: list[str] = field(default_factory=list)
    transitions: list[str] = field(default_factory=list)
    last_error: str | None = None


class GoldenLoopError(RuntimeError):
    pass


class GoldenClosedLoop:
    """Single-owner closed-loop coordinator.

    Callbacks are deliberately narrow. The caller supplies real Brain
    authority/execution/verification components; this class cannot fabricate
    authority or declare success without the verifier returning success.
    """

    def __init__(
        self,
        *,
        evidence_store: Any,
        authorize: Callable[[GoldenTask, int], dict[str, Any]],
        execute: Callable[[GoldenTask, int, str], dict[str, Any]],
        observe: Callable[[GoldenTask, int, dict[str, Any]], dict[str, Any]],
        verify: Callable[[GoldenTask, int, dict[str, Any], dict[str, Any]], dict[str, Any]],
        commit: Callable[[GoldenTask, int, dict[str, Any]], dict[str, Any]],
        learn: Callable[[GoldenTask, int, dict[str, Any]], dict[str, Any]] | None = None,
        recover: Callable[[GoldenTask, int, Exception], dict[str, Any]] | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.evidence = evidence_store
        self.authorize = authorize
        self.execute = execute
        self.observe = observe
        self.verify = verify
        self.commit = commit
        self.learn = learn or (lambda task, attempt, verified: {"ok": True, "status": "LEARN_SKIPPED"})
        self.recover = recover or (lambda task, attempt, error: {"ok": True, "status": "RECOVERY_NOT_REQUIRED"})
        self.sleep = sleep_fn

    @staticmethod
    def fingerprint(task: GoldenTask) -> str:
        raw = json.dumps(
            {"action": task.action, "parameters": task.parameters},
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
        return hashlib.sha256(raw).hexdigest()

    def run(self, task: GoldenTask, *, mission_id: str | None = None) -> dict[str, Any]:
        if not task.task_id.strip() or not task.action.strip():
            raise GoldenLoopError("GOLDEN_TASK_ID_AND_ACTION_REQUIRED")
        if task.max_attempts < 1:
            raise GoldenLoopError("GOLDEN_MAX_ATTEMPTS_INVALID")

        state = GoldenState(
            mission_id=mission_id or "mission-" + uuid4().hex,
            task_id=task.task_id,
            execution_key=f"{mission_id or 'mission'}:{task.task_id}:{self.fingerprint(task)}",
        )
        self._record(state, GoldenPhase.INTENT, {"action": task.action})
        self._record(state, GoldenPhase.PLAN, {"fingerprint": self.fingerprint(task)})

        for attempt in range(1, task.max_attempts + 1):
            state.attempt = attempt
            try:
                state.phase = GoldenPhase.AUTHORITY
                authority = self.authorize(task, attempt)
                if not authority.get("ok") or not authority.get("verified"):
                    raise GoldenLoopError("AUTHORITY_NOT_VERIFIED")

                state.phase = GoldenPhase.ADMIT
                if authority.get("admit", True) is not True:
                    raise GoldenLoopError("WORKLOAD_NOT_ADMITTED")
                self._record(state, GoldenPhase.AUTHORITY, {"verified": True, "attempt": attempt})

                state.phase = GoldenPhase.EXECUTE
                result = self.execute(task, attempt, state.execution_key)
                self._record(state, GoldenPhase.EXECUTE, {"ok": bool(result.get("ok")), "attempt": attempt})

                state.phase = GoldenPhase.OBSERVE
                observation = self.observe(task, attempt, result)
                if not observation.get("ok"):
                    raise GoldenLoopError("OBSERVATION_FAILED")
                self._record(state, GoldenPhase.OBSERVE, observation)

                state.phase = GoldenPhase.VERIFY
                verified = self.verify(task, attempt, result, observation)
                if not verified.get("ok") or verified.get("status") != "VERIFIED":
                    raise GoldenLoopError("INDEPENDENT_VERIFICATION_FAILED")
                self._record(state, GoldenPhase.VERIFY, verified)

                state.phase = GoldenPhase.COMMIT
                committed = self.commit(task, attempt, verified)
                if not committed.get("ok"):
                    raise GoldenLoopError("COMMIT_FAILED")
                self._record(state, GoldenPhase.COMMIT, committed)

                state.phase = GoldenPhase.LEARN
                learned = self.learn(task, attempt, verified)
                if not learned.get("ok"):
                    raise GoldenLoopError("LEARN_FAILED")
                self._record(state, GoldenPhase.LEARN, learned)

                state.phase = GoldenPhase.CLOSED
                state.status = "VERIFIED"
                self._record(state, GoldenPhase.CLOSED, {"status": "GOLDEN_CLOSED_LOOP_VERIFIED"})
                return {
                    "ok": True,
                    "status": "GOLDEN_CLOSED_LOOP_VERIFIED",
                    "mission_id": state.mission_id,
                    "task_id": state.task_id,
                    "attempt": state.attempt,
                    "execution_key": state.execution_key,
                    "evidence_ids": list(state.evidence_ids),
                    "transitions": list(state.transitions),
                }
            except Exception as exc:
                state.last_error = f"{type(exc).__name__}:{exc}"
                self._record(state, GoldenPhase.RECOVER, {"error": state.last_error, "attempt": attempt})
                recovery = self.recover(task, attempt, exc)
                if attempt >= task.max_attempts or not recovery.get("ok"):
                    state.phase = GoldenPhase.FAILED
                    state.status = "FAILED"
                    self._record(state, GoldenPhase.FAILED, recovery)
                    return {
                        "ok": False,
                        "status": "GOLDEN_CLOSED_LOOP_FAILED",
                        "mission_id": state.mission_id,
                        "task_id": state.task_id,
                        "attempt": attempt,
                        "error": state.last_error,
                        "evidence_ids": list(state.evidence_ids),
                        "transitions": list(state.transitions),
                    }
                self.sleep(min(2 ** (attempt - 1), 10))

        raise GoldenLoopError("GOLDEN_LOOP_UNREACHABLE")

    def _record(self, state: GoldenState, phase: GoldenPhase, payload: dict[str, Any]) -> None:
        state.transitions.append(phase.value)
        evidence = self.evidence.append(
            state.task_id,
            f"golden:{phase.value.lower()}",
            {
                "mission_id": state.mission_id,
                "attempt": state.attempt,
                "phase": phase.value,
                "payload": payload,
            },
            producer="brain-golden-loop",
            mission_id=state.mission_id,
            attempt=state.attempt,
            phase=phase.value,
        )
        check = self.evidence.verify_hash(evidence["evidence_id"])
        if not check.get("ok"):
            raise GoldenLoopError("GOLDEN_EVIDENCE_INTEGRITY_FAILED")
        state.evidence_ids.append(evidence["evidence_id"])
