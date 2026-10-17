"""Deterministic APM execution-status classification."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class APMExecutionStatus:
    status: str
    execution_blocker: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return {
            "status": self.status,
            "execution_blocker": self.execution_blocker,
        }


def classify(status: str, conclusion: str | None = None) -> APMExecutionStatus:
    status = (status or "").lower()
    conclusion = (conclusion or "").lower()
    if status == "queued":
        return APMExecutionStatus("WAITING_FOR_RUNNER", "RUNNER_CAPACITY")
    if status in {"in_progress", "running"}:
        return APMExecutionStatus("EXECUTING")
    if conclusion in {"success", "passed"}:
        return APMExecutionStatus("VERIFIED")
    if conclusion in {"failure", "timed_out", "cancelled"}:
        return APMExecutionStatus("EXECUTION_FAILED", conclusion.upper())
    return APMExecutionStatus("UNKNOWN")


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(classify(sys.argv[1] if len(sys.argv) > 1 else "",
                              sys.argv[2] if len(sys.argv) > 2 else None).as_dict()))
