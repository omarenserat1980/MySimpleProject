"""Bounded offline nonce search over a session-bound Stratum job.

No network transport, credentials loading, unbounded mining loop, or pool
submission occurs here. Results are local computation evidence only.
"""
from __future__ import annotations

import hashlib
from typing import Any

from .bitcoin_header import sha256d
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

    Build the session-bound header prefix once, then vary only the four-byte
    nonce and hash each candidate. This avoids rebuilding coinbase and merkle
    data for every attempt. A match is local target evidence only.
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

    # Reuse the existing builder as the single validation and serialization
    # boundary for session/job authorization, dialect, fields, and target.
    seed = build_session_header_candidate(
        session,
        job,
        extranonce2=extranonce2,
        ntime_hex=ntime_hex,
        nonce_hex=f"{nonce_start:08x}",
        share_target=share_target,
        prevhash_dialect_confirmed=prevhash_dialect_confirmed,
    )
    header_prefix = bytes.fromhex(seed["header_hex"][: 76 * 2])
    attempts = 0

    for nonce in range(nonce_start, nonce_start + max_attempts):
        header = header_prefix + nonce.to_bytes(4, "little")
        digest = sha256d(header)
        hash_integer = int.from_bytes(digest, "little")
        meets_target = hash_integer <= share_target
        candidate = {
            "evidence_class": "OFFLINE_SESSION_BOUND_HEADER_CANDIDATE",
            "job_id": job.job_id,
            "header_hex": header.hex(),
            "header_bytes": len(header),
            "nonce_hex": f"{nonce:08x}",
            "sha256d_display_hex": digest[::-1].hex(),
            "hash_integer": hash_integer,
            "share_target": share_target,
            "meets_supplied_share_target": meets_target,
            "session_authorized": True,
            "job_current_for_session": True,
            "prevhash_dialect_confirmed_by_caller": True,
            "pool_submission_sent": False,
            "pool_acceptance_verified": False,
            "real_mining_verified": False,
            "revenue_verified": False,
        }
        attempts += 1
        if meets_target:
            return {
                "evidence_class": "BOUNDED_OFFLINE_NONCE_SEARCH",
                "status": "LOCAL_TARGET_MATCH",
                "attempts": attempts,
                "nonce_start": nonce_start,
                "nonce_found": nonce,
                "candidate": candidate,
                "pool_submission_sent": False,
                "pool_acceptance_verified": False,
                "real_mining_verified": False,
                "revenue_verified": False,
            }

    return {
        "evidence_class": "BOUNDED_OFFLINE_NONCE_SEARCH",
        "status": "NO_LOCAL_TARGET_MATCH_IN_RANGE",
        "attempts": attempts,
        "nonce_start": nonce_start,
        "nonce_found": None,
        "last_candidate": candidate,
        "pool_submission_sent": False,
        "pool_acceptance_verified": False,
        "real_mining_verified": False,
        "revenue_verified": False,
    }
