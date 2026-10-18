"""Bounded offline nonce search over a session-bound Stratum job.

No network transport, credentials loading, unbounded mining loop, or pool
submission occurs here. Results are local computation evidence only.
"""
from __future__ import annotations

from typing import Any

from .stratum_session_header_candidate import build_session_header_candidate
from .stratum_v1_jobs import StratumJob
from .stratum_v1_protocol import StratumV1Session


MAX_NONCE_ATTEMPTS = 4096


def search_session_nonce_range(
    session: StratumV1Session,
    job: StratumJob,
    *,
    extranonce2: str,
    ntime_hex: str,
    nonce_start: int,
    max_attempts: int,
    share_target: int,
    prevhash_dialect_confirmed: bool = False,
) -> dict[str, Any]:
    """Try a finite, caller-bounded sequence of 32-bit nonce values.

    The upper bound is deliberately small to keep this helper suitable for
    tests and diagnostics. No nonce wrapping occurs. A found candidate means
    only that its computed SHA256d integer met the caller-supplied target.
    """
    if isinstance(nonce_start, bool) or not isinstance(nonce_start, int):
        raise ValueError("INVALID_NONCE_START")
    if not 0 <= nonce_start <= 0xFFFFFFFF:
        raise ValueError("NONCE_START_OUT_OF_RANGE")
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int):
        raise ValueError("INVALID_MAX_ATTEMPTS")
    if not 1 <= max_attempts <= MAX_NONCE_ATTEMPTS:
        raise ValueError("MAX_ATTEMPTS_OUT_OF_RANGE")
    if nonce_start + max_attempts - 1 > 0xFFFFFFFF:
        raise ValueError("NONCE_RANGE_OVERFLOWS_UINT32")

    last: dict[str, Any] | None = None
    attempts = 0
    for nonce in range(nonce_start, nonce_start + max_attempts):
        last = build_session_header_candidate(
            session,
            job,
            extranonce2=extranonce2,
            ntime_hex=ntime_hex,
            nonce_hex=f"{nonce:08x}",
            share_target=share_target,
            prevhash_dialect_confirmed=prevhash_dialect_confirmed,
        )
        attempts += 1
        if last["meets_supplied_share_target"]:
            return {
                "evidence_class": "BOUNDED_OFFLINE_NONCE_SEARCH",
                "status": "LOCAL_TARGET_MATCH",
                "attempts": attempts,
                "nonce_start": nonce_start,
                "nonce_found": nonce,
                "candidate": last,
                "pool_submission_sent": False,
                "pool_acceptance_verified": False,
                "real_mining_verified": False,
                "revenue_verified": False,
            }

    assert last is not None
    return {
        "evidence_class": "BOUNDED_OFFLINE_NONCE_SEARCH",
        "status": "NO_LOCAL_TARGET_MATCH_IN_RANGE",
        "attempts": attempts,
        "nonce_start": nonce_start,
        "nonce_found": None,
        "last_candidate": last,
        "pool_submission_sent": False,
        "pool_acceptance_verified": False,
        "real_mining_verified": False,
        "revenue_verified": False,
    }
