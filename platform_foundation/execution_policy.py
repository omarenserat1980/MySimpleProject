"""Brain-owned execution policy.

GitHub is a source/evidence mirror, not the default execution authority.
Autonomous Brain work must run on a Brain-owned executor. If it is unavailable,
the correct result is BLOCKED/DEFERRED, never silent fallback to a hosted runner.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class ExecutionMode(str, Enum):
    BRAIN_ONLY = "BRAIN_ONLY"
    BRAIN_PREFERRED = "BRAIN_PREFERRED"
    EXTERNAL_ALLOWED = "EXTERNAL_ALLOWED"


class ExecutorDecision(str, Enum):
    ALLOWED = "ALLOWED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class ExecutorDescriptor:
    executor_id: str
    owner: str
    persistent: bool
    capabilities: frozenset[str] = frozenset()


@dataclass(frozen=True)
class ExecutionDecision:
    decision: ExecutorDecision
    executor_id: str | None
    reason: str


class BrainExecutionPolicy:
    """Central guard preventing accidental external-runner fallback."""

    def __init__(self, mode: ExecutionMode = ExecutionMode.BRAIN_ONLY) -> None:
        self.mode = mode

    @staticmethod
    def is_brain_owned(executor: ExecutorDescriptor) -> bool:
        return executor.owner.strip().lower() == "brain" and executor.persistent

    def select(
        self,
        executors: list[ExecutorDescriptor],
        *,
        required_capabilities: set[str] | None = None,
    ) -> ExecutionDecision:
        required = set(required_capabilities or ())
        brain = [
            e for e in executors
            if self.is_brain_owned(e) and required.issubset(e.capabilities)
        ]
        if brain:
            return ExecutionDecision(
                ExecutorDecision.ALLOWED, brain[0].executor_id,
                "brain-owned persistent executor selected",
            )

        if self.mode == ExecutionMode.EXTERNAL_ALLOWED:
            external = [
                e for e in executors
                if required.issubset(e.capabilities)
            ]
            if external:
                return ExecutionDecision(
                    ExecutorDecision.ALLOWED, external[0].executor_id,
                    "external executor explicitly allowed by policy",
                )

        return ExecutionDecision(
            ExecutorDecision.BLOCKED,
            None,
            "brain-owned executor unavailable; external fallback forbidden",
        )
