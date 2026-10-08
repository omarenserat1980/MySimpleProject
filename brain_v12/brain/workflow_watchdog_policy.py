"""Policy helpers for the Brain Global Workflow Watchdog.

Recovery must be scoped to the commit that produced the observed workflow run.
This module is intentionally stdlib-only so the policy can be tested independently
of GitHub Actions and reused by the watchdog workflow.
"""

from __future__ import annotations

from typing import Any, Iterable


def partition_failures(
    rows: Iterable[dict[str, Any]], target_sha: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (eligible, ignored_cross_sha) failures for one target SHA."""
    target_sha = (target_sha or "").strip()
    if not target_sha:
        return [], list(rows)

    eligible: list[dict[str, Any]] = []
    ignored: list[dict[str, Any]] = []
    for row in rows:
        if (row.get("head_sha") or "").strip() == target_sha:
            eligible.append(row)
        else:
            ignored.append(row)
    return eligible, ignored


def recovery_allowed(row: dict[str, Any], target_sha: str) -> bool:
    """Defence-in-depth guard for any individual recovery action."""
    return bool(target_sha) and (row.get("head_sha") or "").strip() == target_sha


def select_recovery_candidates(
    rows: Iterable[dict[str, Any]], target_sha: str, limit: int = 1
) -> list[dict[str, Any]]:
    """Select a bounded number of recoveries for one watchdog invocation.

    The global watchdog is an orchestrator, not a fan-out executor.  A single
    invocation may initiate at most one automatic recovery action.
    """
    if limit < 1:
        return []
    eligible, _ = partition_failures(rows, target_sha)
    allowed = [row for row in eligible if recovery_allowed(row, target_sha)]
    allowed.sort(
        key=lambda row: (
            int(row.get("attempt") or 1),
            str(row.get("created_at") or ""),
            int(row.get("run_id") or 0),
        )
    )
    return allowed[:limit]
