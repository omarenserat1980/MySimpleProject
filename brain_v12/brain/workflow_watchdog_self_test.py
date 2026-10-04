"""Adversarial, deterministic self-test for watchdog SHA isolation.

The synthetic failures deliberately mix target and unrelated commits. The
resulting JSON is intended to be retained as CI evidence.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from brain_v12.brain.workflow_watchdog_policy import (
    partition_failures,
    recovery_allowed,
)


def run_self_test() -> dict[str, object]:
    target_sha = "a" * 40
    unrelated_sha = "b" * 40
    failures = [
        {"run_id": 81001, "workflow": "target-failure-one", "head_sha": target_sha},
        {"run_id": 81002, "workflow": "unrelated-old-failure", "head_sha": unrelated_sha},
        {"run_id": 81003, "workflow": "target-failure-two", "head_sha": target_sha},
        {"run_id": 81004, "workflow": "missing-sha-failure", "head_sha": ""},
    ]

    eligible, ignored = partition_failures(failures, target_sha)
    target_allowed = all(recovery_allowed(row, target_sha) for row in eligible)
    unrelated_rejected = all(
        not recovery_allowed(row, target_sha) for row in failures if row["head_sha"] != target_sha
    )
    partition_exact = (
        [row["run_id"] for row in eligible] == [81001, 81003]
        and [row["run_id"] for row in ignored] == [81002, 81004]
    )

    checks = {
        "target_failures_eligible": target_allowed,
        "unrelated_and_missing_sha_recovery_rejected": unrelated_rejected,
        "mixed_records_partitioned_exactly": partition_exact,
    }
    result: dict[str, object] = {
        "test": "brain_workflow_watchdog_adversarial_sha_isolation",
        "schema_version": 1,
        "target_sha": target_sha,
        "synthetic_failures": failures,
        "eligible_for_recovery": [row["run_id"] for row in eligible],
        "ignored_failures": [row["run_id"] for row in ignored],
        "recovery_allowed": {
            str(row["run_id"]): recovery_allowed(row, target_sha) for row in failures
        },
        "checks": checks,
        "passed": all(checks.values()),
    }
    if not result["passed"]:
        raise AssertionError(f"Watchdog adversarial self-test failed: {checks}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--evidence",
        type=Path,
        default=Path("brain6_artifacts/workflow_watchdog/self-test-evidence.json"),
    )
    args = parser.parse_args()

    result = run_self_test()
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("WATCHDOG_SELF_TEST=PASS")
    print(f"WATCHDOG_SELF_TEST_TARGET_SHA={result['target_sha']}")
    print(f"WATCHDOG_SELF_TEST_ELIGIBLE={len(result['eligible_for_recovery'])}")
    print(f"WATCHDOG_SELF_TEST_IGNORED={len(result['ignored_failures'])}")
    print(f"WATCHDOG_SELF_TEST_EVIDENCE={args.evidence}")


if __name__ == "__main__":
    main()
