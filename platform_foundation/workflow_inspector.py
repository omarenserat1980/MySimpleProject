from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .repair_policy import FailureClass, RepairPolicy, RepairScope


@dataclass(frozen=True)
class InspectionResult:
    target_sha: str
    observed_sha: str
    evidence: str
    failure_class: FailureClass
    scope: RepairScope


class WorkflowInspector:
    """Deterministically inspect failure evidence before repair admission."""

    def __init__(self, policy: RepairPolicy | None = None) -> None:
        self.policy = policy or RepairPolicy()

    def inspect(self, record: Mapping[str, object], *, target_sha: str) -> InspectionResult:
        observed_sha = str(record.get("sha") or record.get("head_sha") or "")
        evidence = str(
            record.get("error")
            or record.get("message")
            or record.get("logs")
            or ""
        )
        scope = self.policy.admit(
            evidence,
            target_sha=target_sha,
            observed_sha=observed_sha,
        )
        return InspectionResult(
            target_sha=target_sha,
            observed_sha=observed_sha,
            evidence=evidence,
            failure_class=scope.failure_class,
            scope=scope,
        )


__all__ = ["InspectionResult", "WorkflowInspector"]
