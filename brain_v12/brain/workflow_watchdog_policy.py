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
