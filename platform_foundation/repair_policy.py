from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any


class FailureClass(str, Enum):
    EXECUTION_INFRA = "EXECUTION_INFRA"
    DEPENDENCY = "DEPENDENCY"
    ARTIFACT = "ARTIFACT"
    VERIFICATION = "VERIFICATION"
    UNKNOWN = "UNKNOWN"


class RepairAction(str, Enum):
    RERUN = "RERUN"
    REBUILD_ARTIFACT = "REBUILD_ARTIFACT"
    BLOCK_FOR_REVIEW = "BLOCK_FOR_REVIEW"


@dataclass(frozen=True)
class RepairScope:
    failure_class: FailureClass
    action: RepairAction
    allowed: bool
    reason: str


class RepairPolicy:
    """Brain-independent, bounded failure classification and repair admission."""

    _RULES = (
        (FailureClass.VERIFICATION, re.compile(r"verification|assertion|qc|quality gate", re.I)),
        (FailureClass.DEPENDENCY, re.compile(r"ModuleNotFoundError|ImportError|dependency", re.I)),
        (FailureClass.ARTIFACT, re.compile(r"artifact.*(?:missing|not found)|No such file|cannot open", re.I)),
        (FailureClass.EXECUTION_INFRA, re.compile(r"timeout|timed out|runner|queued|rate limit|502|503", re.I)),
    )

    _ALLOWED = {
        FailureClass.EXECUTION_INFRA: RepairAction.RERUN,
        FailureClass.ARTIFACT: RepairAction.REBUILD_ARTIFACT,
    }

    def classify(self, evidence: str) -> FailureClass:
        text = str(evidence or "")
        for failure_class, pattern in self._RULES:
            if pattern.search(text):
                return failure_class
        return FailureClass.UNKNOWN

    def scope(self, evidence: str) -> RepairScope:
        failure_class = self.classify(evidence)
        action = self._ALLOWED.get(failure_class)
        if action is None:
            return RepairScope(
                failure_class=failure_class,
                action=RepairAction.BLOCK_FOR_REVIEW,
                allowed=False,
                reason="repair is outside the bounded automatic scope",
            )
        return RepairScope(
            failure_class=failure_class,
            action=action,
            allowed=True,
            reason="failure class has an explicitly allowlisted bounded action",
        )

    def admit(self, evidence: str, *, target_sha: str, observed_sha: str) -> RepairScope:
        scope = self.scope(evidence)
        if not target_sha or target_sha != observed_sha:
            return RepairScope(
                failure_class=scope.failure_class,
                action=RepairAction.BLOCK_FOR_REVIEW,
                allowed=False,
                reason="workflow evidence does not match the target commit",
            )
        return scope

    def evidence(self, scope: RepairScope) -> dict[str, Any]:
        return {
            "failure_class": scope.failure_class.value,
            "repair_action": scope.action.value,
            "allowed": scope.allowed,
            "reason": scope.reason,
        }


__all__ = ["FailureClass", "RepairAction", "RepairScope", "RepairPolicy"]
