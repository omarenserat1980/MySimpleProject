"""Brain-owned bounded SHA256d compute job runner.

This is an explicitly invoked, local software compute primitive. It accepts a
validated 80-byte header and target, enforces hard hash/time ceilings, and
returns only an unsubmitted candidate. It never opens a network connection,
loads credentials, starts a background loop, or submits shares.
"""
from __future__ import annotations

import time
from typing import Any

from .brain_owned_compute_runtime import (
    MAX_NONCE_SEARCH_HASHES,
    search_nonce,
    validate_header,
    validate_target,
)

MAX_JOB_SECONDS = 30.0
MAX_JOB_HASHES = min(MAX_NONCE_SEARCH_HASHES, 10_000_000)
_HASH_CHUNK = 10_000


def run_bounded_compute_job(
    header: bytes,
    target: int,
    *,
    max_hashes: int = 100_000,
    max_seconds: float = 5.0,
    start_nonce: int = 0,
) -> dict[str, Any]:
    """Run one synchronous, bounded nonce-search job with no network effects.

    The caller supplies an already validated header and share target. Stratum
    target negotiation, header assembly, pool authorization, and submission
    are intentionally outside this function. A found candidate is not a share
    accepted by a pool.
    """
    validate_header(header)
    validate_target(target)
    if isinstance(max_hashes, bool) or not isinstance(max_hashes, int) or not 1 <= max_hashes <= MAX_JOB_HASHES:
        raise ValueError("MAX_HASHES_OUT_OF_RANGE")
    if isinstance(start_nonce, bool) or not isinstance(start_nonce, int) or not 0 <= start_nonce <= 0xFFFFFFFF:
        raise ValueError("START_NONCE_OUT_OF_RANGE")
    if isinstance(max_seconds, bool) or not isinstance(max_seconds, (int, float)):
        raise ValueError("MAX_SECONDS_OUT_OF_RANGE")
    seconds = float(max_seconds)
    if not 0.01 <= seconds <= MAX_JOB_SECONDS:
        raise ValueError("MAX_SECONDS_OUT_OF_RANGE")

    started = time.monotonic()
    deadline = started + seconds
    checked = 0
    next_nonce = start_nonce
    candidate = None
    status = "HASH_BUDGET_EXHAUSTED"
    while checked < max_hashes and next_nonce <= 0xFFFFFFFF:
        if time.monotonic() >= deadline:
            status = "TIME_BUDGET_EXHAUSTED"
            break
        count = min(_HASH_CHUNK, max_hashes - checked, 0x1_0000_0000 - next_nonce)
        if count <= 0:
            break
        result = search_nonce(header, target, start_nonce=next_nonce, max_hashes=count)
        checked += result.hashes_checked
        next_nonce += result.hashes_checked
        if result.found:
            candidate = {
                "nonce": result.nonce,
                "hash_hex": result.hash_hex,
                "status": "NONCE_FOUND_UNSUBMITTED",
            }
            status = "NONCE_FOUND_UNSUBMITTED"
            break
        if result.hashes_checked < count:
            status = "NONCE_SPACE_EXHAUSTED"
            break
    else:
        if next_nonce > 0xFFFFFFFF:
            status = "NONCE_SPACE_EXHAUSTED"

    elapsed = max(0.0, time.monotonic() - started)
    return {
        "schema_version": "1.0",
        "status": status,
        "hashes_checked": checked,
        "elapsed_seconds": round(elapsed, 6),
        "hashes_per_second": round(checked / elapsed, 2) if elapsed > 0 else None,
        "candidate": candidate,
        "next_nonce": next_nonce if next_nonce <= 0xFFFFFFFF else None,
        "hard_hash_limit": MAX_JOB_HASHES,
        "hard_time_limit_seconds": MAX_JOB_SECONDS,
        "network_access_performed": False,
        "pool_contacted": False,
        "credentials_loaded": False,
        "share_submitted": False,
        "pool_acceptance_verified": False,
        "real_mining_verified": False,
        "revenue_verified": False,
        "evidence_class": "LOCAL_BOUNDED_SHA256D_COMPUTE_ONLY",
    }
