"""Brain supervisor-facing facade for controlled ASIC self-modification review.

This service evaluates evidence supplied by CI and a candidate diff. It does not
execute arbitrary patches, run shell commands, merge PRs, or deploy to hardware.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from .asic_self_modification_gate import evaluate_asic_change


def review_candidate(
    *,
    candidate_branch: str,
    changed_paths: Sequence[str],
    check_results: Mapping[str, str],
    human_approved_protected_paths: bool = False,
) -> dict[str, Any]:
    """Single entry point for Brain to review an ASIC patch candidate."""
    result = evaluate_asic_change(
        candidate_branch=candidate_branch,
        changed_paths=changed_paths,
        checks=check_results,
        explicit_human_approval=human_approved_protected_paths,
    )
    result["service"] = "brain.asic_self_modification_service"
    result["autonomous_execution_enabled"] = False
    result["merge_enabled"] = False
    result["device_write_enabled"] = False
    return result
