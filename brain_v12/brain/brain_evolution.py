"""Operational evolution metrics for the Electronic Brain.

The score is intentionally evidence-based: it measures completed workflow outcomes
and bounded recovery behavior from GitHub Actions data supplied as JSON.
It does not claim intelligence or consciousness.
"""
from __future__ import annotations
import json
import sys
from statistics import mean


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def calculate(runs: list[dict]) -> dict:
    completed = [r for r in runs if r.get("status") == "completed"]
    successful = [r for r in completed if r.get("conclusion") == "success"]
    failed = [r for r in completed if r.get("conclusion") in {"failure", "timed_out", "cancelled"}]

    completion_rate = 100.0 * len(successful) / len(completed) if completed else 0.0
    first_pass = [r for r in completed if int(r.get("run_attempt") or 1) == 1]
    first_pass_success = [r for r in first_pass if r.get("conclusion") == "success"]
    first_pass_rate = 100.0 * len(first_pass_success) / len(first_pass) if first_pass else 0.0

    recovered = [r for r in successful if int(r.get("run_attempt") or 1) > 1]
    recovery_attempts = [r for r in completed if int(r.get("run_attempt") or 1) > 1]
    recovery_rate = 100.0 * len(recovered) / len(recovery_attempts) if recovery_attempts else 100.0

    regression_rate = 100.0 * len(failed) / len(completed) if completed else 100.0

    score = (
        completion_rate * 0.40
        + first_pass_rate * 0.20
        + recovery_rate * 0.20
        + (100.0 - regression_rate) * 0.20
    )

    return {
        "schema": "brain.evolution.v1",
        "sample_size": len(runs),
        "completed_runs": len(completed),
        "successful_runs": len(successful),
        "failed_runs": len(failed),
        "recovery_attempts": len(recovery_attempts),
        "recovered_successes": len(recovered),
        "metrics": {
            "completion_rate": round(completion_rate, 2),
            "first_pass_rate": round(first_pass_rate, 2),
            "recovery_success_rate": round(recovery_rate, 2),
            "regression_rate": round(regression_rate, 2),
        },
        "evolution_index": round(_clamp(score), 2),
        "interpretation": (
            "measured operational improvement"
            if completed and score >= 80
            else "operational state requires more evidence"
        ),
    }


def main() -> int:
    payload = json.load(sys.stdin)
    runs = payload.get("workflow_runs", payload if isinstance(payload, list) else [])
    result = calculate(runs)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
