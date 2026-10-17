"""Local proof-of-work candidate validation for Electronic Brain.

This adapter binds a locally computed SHA256d nonce candidate to a specific job
and target. It performs no network I/O, never reads credentials, and never
submits a share. A valid local candidate is not evidence of pool acceptance.
"""
from __future__ import annotations

import hashlib
from typing import Any

from brain_v12.brain.brain_owned_compute_runtime import (
    double_sha256,
    validate_header,
    validate_target,
)


def validate_share_candidate(
    *,
    header: bytes,
    target: int,
    nonce: int,
    job_id: str,
    expected_job_id: str,
) -> dict[str, Any]:
    """Validate a candidate against the exact job ID, header nonce and target."""
    validate_header(header)
    validate_target(target)
    if not isinstance(job_id, str) or not job_id or len(job_id) > 256:
        raise ValueError("INVALID_JOB_ID")
    if not isinstance(expected_job_id, str) or not expected_job_id or len(expected_job_id) > 256:
        raise ValueError("INVALID_EXPECTED_JOB_ID")
    if job_id != expected_job_id:
        raise ValueError("SHARE_JOB_ID_MISMATCH")
    if isinstance(nonce, bool) or not isinstance(nonce, int) or not 0 <= nonce <= 0xFFFFFFFF:
        raise ValueError("NONCE_OUT_OF_RANGE")
    header_nonce = int.from_bytes(header[76:80], "little")
    if nonce != header_nonce:
        raise ValueError("HEADER_NONCE_MISMATCH")

    digest = double_sha256(header)
    hash_value = int.from_bytes(digest, "little")
    meets_target = hash_value <= target
    return {
        "status": "VALID_LOCAL_CANDIDATE_UNSUBMITTED" if meets_target else "INVALID_LOCAL_CANDIDATE",
        "job_id": job_id,
        "header_sha256": hashlib.sha256(header).hexdigest(),
        "nonce": nonce,
        "hash_hex": digest[::-1].hex(),
        "target_hex": f"{target:064x}",
        "meets_target": meets_target,
        "pool_submission_attempted": False,
        "pool_acceptance_verified": False,
        "counts_as_real_pool_mining": False,
        "evidence_class": "LOCAL_PROOF_OF_WORK_CANDIDATE_ONLY",
    }
