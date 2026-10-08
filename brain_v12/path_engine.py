"""Unified Path Engine V1 for Electronic Brain.

A small, dependency-free orchestration kernel. Paths describe work; the engine
enforces one active run per goal, attempt budgets, gates, evidence, and
terminal states. Executors are injected by callers so this module does not
perform external side effects by itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from time import time
from typing import Any, Callable, Dict, List, Optional


class PathState(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    WAITING_GATE = "WAITING_GATE"
    VERIFYING = "VERIFYING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    STOPPED = "STOPPED"


class GateDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    WAIT = "WAIT"


@dataclass(frozen=True)
class GateResult:
    decision: GateDecision
    reason: str = ""


@dataclass
class Evidence:
    kind: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time)


@dataclass
class PathSpec:
    path_id: str
    goal: str
    steps: List[str]
    max_attempts: int = 3
    max_steps: int = 32
    require_authorization: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PathRun:
    run_id: str
    spec: PathSpec
    state: PathState = PathState.CREATED
    step_index: int = 0
    attempts: int = 0
    evidence: List[Evidence] = field(default_factory=list)
    last_error: Optional[str] = None

    @property
    def current_step(self) -> Optional[str]:
        if 0 <= self.step_index < len(self.spec.steps):
            return self.spec.steps[self.step_index]
        return None

    def add_evidence(self, kind: str, message: str, **data: Any) -> None:
        self.evidence.append(Evidence(kind, message, data))


Executor = Callable[[PathRun, str], Any]
Gate = Callable[[PathRun], GateResult]
Verifier = Callable[[PathRun, Any], bool]


class PathEngine:
    """Single-owner path orchestrator.

    The engine is intentionally synchronous and single-active-run per goal.
    This is the V1 safety boundary against runaway repair/CI loops.
    """

    def __init__(
        self,
        *,
        authorization_gate: Optional[Gate] = None,
        policy_gate: Optional[Gate] = None,
        executor: Optional[Executor] = None,
        verifier: Optional[Verifier] = None,
    ) -> None:
        self.authorization_gate = authorization_gate
        self.policy_gate = policy_gate
        self.executor = executor
        self.verifier = verifier
        self.active_by_goal: Dict[str, str] = {}
        self.runs: Dict[str, PathRun] = {}

    def start(self, spec: PathSpec, run_id: str) -> PathRun:
        if not spec.path_id or not spec.goal or not spec.steps:
            raise ValueError("path_id, goal and steps are required")
        if spec.max_attempts < 1 or spec.max_steps < 1:
            raise ValueError("budgets must be positive")
        if spec.max_steps < len(spec.steps):
            raise ValueError("max_steps cannot be smaller than path length")
        if spec.goal in self.active_by_goal:
            active_id = self.active_by_goal[spec.goal]
            active = self.runs[active_id]
            if active.state in {
                PathState.CREATED,
                PathState.RUNNING,
                PathState.WAITING_GATE,
                PathState.VERIFYING,
            }:
                raise RuntimeError(f"goal already active: {spec.goal}")

        run = PathRun(run_id=run_id, spec=spec)
        self.runs[run_id] = run
        self.active_by_goal[spec.goal] = run_id
        run.add_evidence("path_created", "Path run created", path_id=spec.path_id)
        return run

    def _gate(self, gate: Optional[Gate], run: PathRun, name: str) -> GateResult:
        if gate is None:
            return GateResult(GateDecision.ALLOW)
        result = gate(run)
        if result.decision != GateDecision.ALLOW:
            run.add_evidence("gate", f"{name}: {result.decision.value}", reason=result.reason)
        return result

    def advance(self, run_id: str) -> PathRun:
        run = self.runs[run_id]
        if run.state in {
            PathState.SUCCEEDED,
            PathState.BLOCKED,
            PathState.STOPPED,
        }:
            return run

        if run.attempts >= run.spec.max_attempts:
            run.state = PathState.STOPPED
            run.last_error = "attempt budget exhausted"
            run.add_evidence("budget", "Attempt budget exhausted", attempts=run.attempts)
            self._release(run)
            return run

        if run.step_index >= len(run.spec.steps):
            run.state = PathState.SUCCEEDED
            run.add_evidence("complete", "Path completed")
            self._release(run)
            return run

        auth = self._gate(self.authorization_gate, run, "authorization")
        if auth.decision == GateDecision.DENY:
            run.state = PathState.BLOCKED
            run.last_error = auth.reason or "authorization denied"
            self._release(run)
            return run
        if auth.decision == GateDecision.WAIT:
            run.state = PathState.WAITING_GATE
            return run

        policy = self._gate(self.policy_gate, run, "policy")
        if policy.decision == GateDecision.DENY:
            run.state = PathState.BLOCKED
            run.last_error = policy.reason or "policy denied"
            self._release(run)
            return run
        if policy.decision == GateDecision.WAIT:
            run.state = PathState.WAITING_GATE
            return run

        if self.executor is None:
            run.state = PathState.BLOCKED
            run.last_error = "no executor configured"
            run.add_evidence("executor", "No executor configured")
            self._release(run)
            return run

        run.state = PathState.RUNNING
        step = run.current_step
        run.attempts += 1
        try:
            result = self.executor(run, step)
            run.add_evidence("execution", "Step executed", step=step, result=result)
        except Exception as exc:  # executor boundary
            run.last_error = f"{type(exc).__name__}: {exc}"
            run.state = (
                PathState.STOPPED
                if run.attempts >= run.spec.max_attempts
                else PathState.FAILED
            )
            run.add_evidence("failure", "Step execution failed", step=step, error=run.last_error)
            if run.state in {PathState.STOPPED, PathState.FAILED}:
                if run.state == PathState.STOPPED:
                    self._release(run)
                return run

        run.state = PathState.VERIFYING
        verified = self.verifier(run, result) if self.verifier else True
        run.add_evidence("verification", "Step verified" if verified else "Step rejected", step=step)

        if not verified:
            run.state = (
                PathState.STOPPED
                if run.attempts >= run.spec.max_attempts
                else PathState.FAILED
            )
            run.last_error = "verification failed"
            if run.state == PathState.STOPPED:
                self._release(run)
            return run

        run.step_index += 1
        run.state = (
            PathState.SUCCEEDED
            if run.step_index >= len(run.spec.steps)
            else PathState.RUNNING
        )
        if run.state == PathState.SUCCEEDED:
            run.add_evidence("complete", "Path completed")
            self._release(run)
        return run

    def stop(self, run_id: str, reason: str = "stopped by controller") -> PathRun:
        run = self.runs[run_id]
        if run.state not in {
            PathState.SUCCEEDED,
            PathState.FAILED,
            PathState.BLOCKED,
            PathState.STOPPED,
        }:
            run.state = PathState.STOPPED
            run.last_error = reason
            run.add_evidence("stop", reason)
            self._release(run)
        return run

    def _release(self, run: PathRun) -> None:
        if self.active_by_goal.get(run.spec.goal) == run.run_id:
            del self.active_by_goal[run.spec.goal]
