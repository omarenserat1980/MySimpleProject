from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .repair_policy import RepairAction, RepairPolicy, RepairScope


@dataclass(frozen=True)
class RepairResult:
    attempted: bool
    succeeded: bool
    attempts: int
    scope: RepairScope
    reason: str


class BoundedRepairExecutor:
    """Execute only policy-approved repair callbacks with a hard attempt bound."""

    def __init__(self, policy: RepairPolicy | None = None, *, max_attempts: int = 1) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        self.policy = policy or RepairPolicy()
        self.max_attempts = max_attempts

    def execute(
        self,
        evidence: str,
        *,
        target_sha: str,
        observed_sha: str,
        rerun: Callable[[], bool] | None = None,
        rebuild_artifact: Callable[[], bool] | None = None,
        verify: Callable[[], bool] | None = None,
    ) -> RepairResult:
        scope = self.policy.admit(
            evidence,
            target_sha=target_sha,
            observed_sha=observed_sha,
        )
        if not scope.allowed:
            return RepairResult(False, False, 0, scope, scope.reason)

        action = scope.action
        callback = {
            RepairAction.RERUN: rerun,
            RepairAction.REBUILD_ARTIFACT: rebuild_artifact,
        }.get(action)
        if callback is None or verify is None:
            blocked = RepairScope(
                scope.failure_class,
                RepairAction.BLOCK_FOR_REVIEW,
                False,
                "approved repair requires both an execution callback and an independent verifier",
            )
            return RepairResult(False, False, 0, blocked, blocked.reason)

        attempts = 0
        for _ in range(self.max_attempts):
            attempts += 1
            try:
                if not callback():
                    continue
                if verify():
                    return RepairResult(True, True, attempts, scope, "repair completed and independently verified")
            except Exception:
                continue

        return RepairResult(True, False, attempts, scope, "bounded repair attempts exhausted or verification failed")


__all__ = ["BoundedRepairExecutor", "RepairResult"]
