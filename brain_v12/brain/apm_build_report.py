"""Portable APM build report and next-action decision."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class APMBuildReport:
    status: str
    next_action: str
    completed: int
    blocked: int
    cached: int
    failed: int
    runner_status: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "next_action": self.next_action,
            "completed": self.completed,
            "blocked": self.blocked,
            "cached": self.cached,
            "failed": self.failed,
            "runner_status": self.runner_status,
        }


def build_report(
    *,
    completed: int = 0,
    blocked: int = 0,
    cached: int = 0,
    failed: int = 0,
    runner_status: str = "unknown",
) -> APMBuildReport:
    runner = runner_status.upper()
    if runner in {"QUEUED", "WAITING_FOR_RUNNER"}:
        return APMBuildReport(
            "WAITING_FOR_RUNNER", "RESUME_WHEN_RUNNER_AVAILABLE",
            completed, blocked, cached, failed, runner,
        )
    if failed:
        return APMBuildReport(
            "FAILED", "RETRY_FAILED_UNITS_ONLY",
            completed, blocked, cached, failed, runner,
        )
    if blocked:
        return APMBuildReport(
            "BLOCKED", "INSPECT_BLOCKING_DEPENDENCY",
            completed, blocked, cached, failed, runner,
        )
    return APMBuildReport(
        "VERIFIED", "PROCEED_TO_NEXT_GATE",
        completed, blocked, cached, failed, runner,
    )
