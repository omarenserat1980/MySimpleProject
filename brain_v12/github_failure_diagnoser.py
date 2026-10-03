"""Classify GitHub Actions failures into actionable supervisor decisions."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class FailureDiagnosis:
    category: str
    retryable: bool
    repair: str
    reason: str

def diagnose(job: dict, logs: str = "") -> FailureDiagnosis:
    conclusion = (job.get("conclusion") or "").lower()
    steps = job.get("steps") or []
    if conclusion == "cancelled":
        return FailureDiagnosis(
            "cancelled",
            True,
            "rerun",
            "The GitHub Actions job was cancelled before the pipeline reached its execution gates."
        )
    text = (logs or "").lower()
    if "the operation was canceled" in text or "operation was cancelled" in text:
        return FailureDiagnosis(
            "transient_cancellation",
            True,
            "rerun",
            "Runner operation was cancelled; this is not sufficient evidence of a code defect."
        )
    failed = [s.get("name") for s in steps if s.get("conclusion") == "failure"]
    if failed:
        return FailureDiagnosis(
            "step_failure",
            False,
            "inspect_and_patch",
            "A concrete workflow step failed: " + ", ".join(failed)
        )
    if conclusion == "failure":
        return FailureDiagnosis(
            "unknown_failure",
            False,
            "inspect_logs",
            "The run failed without a classified step-level cause."
        )
    return FailureDiagnosis("unknown", False, "inspect_logs", "No actionable failure evidence found.")
