"""Audited, read-only ASIC candidate review entry point for Brain Supervisor.

This bridge records a policy decision in the supervisor audit stream. It does
not execute patches, invoke shell commands, merge PRs, or write to devices.
"""
from __future__ import annotations

from typing import Mapping, Sequence, Any

from .asic_self_modification_service import review_candidate


def review_candidate_with_supervisor(
    supervisor: Any,
    *,
    job_id: str,
    candidate_branch: str,
    changed_paths: Sequence[str],
    check_results: Mapping[str, str],
    human_approved_protected_paths: bool = False,
) -> dict[str, Any]:
    """Review a candidate and append the decision to the supervisor's audit log."""
    if not isinstance(job_id, str) or not job_id.strip():
        raise ValueError("JOB_ID_REQUIRED")
    result = review_candidate(
        candidate_branch=candidate_branch,
        changed_paths=changed_paths,
        check_results=check_results,
        human_approved_protected_paths=human_approved_protected_paths,
    )
    event_data = {
        "decision": result["decision"],
        "candidate_branch": result["candidate_branch"],
        "changed_paths": result["changed_paths"],
        "reasons": result["reasons"],
        "checks": result["checks"],
        "deployment_authorized": result["deployment_authorized"],
        "firmware_flash_authorized": result["firmware_flash_authorized"],
        "real_mining_verified": result["real_mining_verified"],
        "revenue_verified": result["revenue_verified"],
        "autonomous_execution_enabled": result["autonomous_execution_enabled"],
        "merge_enabled": result["merge_enabled"],
        "device_write_enabled": result["device_write_enabled"],
    }
    supervisor._event(job_id, "asic_self_modification_review", event_data)
    return result
