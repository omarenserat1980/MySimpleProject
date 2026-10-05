from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from .repair_executor import RepairResult
from .workflow_inspector import InspectionResult


@dataclass(frozen=True)
class RepairEvidence:
    target_sha: str
    observed_sha: str
    failure_class: str
    repair_action: str
    allowed: bool
    attempted: bool
    succeeded: bool
    attempts: int
    reason: str
    recorded_at: str

    @classmethod
    def from_results(
        cls,
        inspection: InspectionResult,
        result: RepairResult,
    ) -> "RepairEvidence":
        return cls(
            target_sha=inspection.target_sha,
            observed_sha=inspection.observed_sha,
            failure_class=result.scope.failure_class.value,
            repair_action=result.scope.action.value,
            allowed=result.scope.allowed,
            attempted=result.attempted,
            succeeded=result.succeeded,
            attempts=result.attempts,
            reason=result.reason,
            recorded_at=datetime.now(timezone.utc).isoformat(),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evidence_is_complete(record: Mapping[str, object]) -> bool:
    required = {
        "target_sha",
        "observed_sha",
        "failure_class",
        "repair_action",
        "allowed",
        "attempted",
        "succeeded",
        "attempts",
        "reason",
        "recorded_at",
    }
    return required.issubset(record.keys())


__all__ = ["RepairEvidence", "evidence_is_complete"]
