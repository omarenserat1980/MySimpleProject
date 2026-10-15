"""Fail-closed policy gate for Brain's proposed ASIC self-modifications.

This module evaluates a proposed change; it does not edit files, run commands,
merge pull requests, flash firmware, or deploy to a physical device.
"""
from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any, Mapping, Sequence

REQUIRED_CHECKS = ("unit", "rtl", "synthesis", "security")
ALLOWED_PREFIXES = ("brain_v12/asic/", "brain_v12/tests/", "docs/")
FORBIDDEN_PARTS = {".git", ".github", "secrets", "credentials", "wallet"}
FORBIDDEN_NAMES = {".env", "id_rsa", "id_ed25519", "authorized_keys"}
PROTECTED_PREFIXES = (
    "brain_v12/brain/",
    ".github/workflows/",
)


def evaluate_asic_change(
    *,
    candidate_branch: str,
    changed_paths: Sequence[str],
    checks: Mapping[str, str],
    explicit_human_approval: bool = False,
) -> dict[str, Any]:
    """Return a review decision; never authorizes deployment or real mining."""
    reasons: list[str] = []
    normalized: list[str] = []

    if not candidate_branch or candidate_branch in {"main", "master"}:
        reasons.append("DIRECT_MAIN_MODIFICATION_FORBIDDEN")
    if not changed_paths:
        reasons.append("NO_CHANGED_PATHS")

    for raw in changed_paths:
        if not isinstance(raw, str) or not raw or "\\" in raw:
            reasons.append("INVALID_CHANGED_PATH")
            continue
        path = PurePosixPath(raw)
        if path.is_absolute() or ".." in path.parts:
            reasons.append("PATH_TRAVERSAL_OR_ABSOLUTE_PATH")
            continue
        value = path.as_posix()
        normalized.append(value)
        lower_parts = {part.lower() for part in path.parts}
        if lower_parts & FORBIDDEN_PARTS or path.name.lower() in FORBIDDEN_NAMES:
            reasons.append("SENSITIVE_PATH_FORBIDDEN")
        if not value.startswith(ALLOWED_PREFIXES):
            reasons.append("PATH_OUTSIDE_INITIAL_ASIC_ALLOWLIST")
        if value.startswith(PROTECTED_PREFIXES) and not explicit_human_approval:
            reasons.append("PROTECTED_CONTROL_PLANE_CHANGE_REQUIRES_HUMAN_APPROVAL")

    for check in REQUIRED_CHECKS:
        status = checks.get(check)
        if status != "passed":
            reasons.append(
                f"CHECK_{check.upper()}_{'MISSING' if status is None else str(status).upper()}"
            )

    reasons = sorted(set(reasons))
    return {
        "decision": "READY_FOR_REVIEW" if not reasons else "REJECT",
        "reasons": reasons,
        "candidate_branch": candidate_branch,
        "changed_paths": sorted(set(normalized)),
        "checks": {name: checks.get(name, "missing") for name in REQUIRED_CHECKS},
        "deployment_authorized": False,
        "firmware_flash_authorized": False,
        "real_mining_verified": False,
        "revenue_verified": False,
        "note": "READY_FOR_REVIEW is not approval to merge, deploy, flash firmware, mine, or claim revenue.",
    }
