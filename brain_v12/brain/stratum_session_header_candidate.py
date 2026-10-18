"""Build an offline Bitcoin header candidate from a validated Stratum session/job.

This module computes a candidate only. It does not scan nonces, connect to a
pool, submit shares, or claim acceptance/revenue. The caller must supply the
share target and confirm the pool's documented Stratum prevhash dialect.
"""
from __future__ import annotations

from typing import Any

from .bitcoin_header import (
    build_header_candidate,
    stratum_v1_prevhash_to_header_wire_hex,
)
from .stratum_v1_jobs import StratumJob, build_coinbase, merkle_root_from_coinbase
from .stratum_v1_protocol import StratumProtocolError, StratumV1Session


def build_session_header_candidate(
    session: StratumV1Session,
    job: StratumJob,
    *,
    extranonce2: str,
    ntime_hex: str,
    nonce_hex: str,
    share_target: int,
    prevhash_dialect_confirmed: bool = False,
) -> dict[str, Any]:
    """Construct and hash an 80-byte candidate bound to current session state.

    A caller must explicitly confirm that the pool uses the legacy Stratum V1
    eight-word prevhash encoding before that conversion is applied. The supplied
    target is used as-is; no pool difficulty or target is inferred.
    """
    if not isinstance(session, StratumV1Session):
        raise StratumProtocolError("STRATUM_V1_SESSION_REQUIRED")
    if not isinstance(job, StratumJob):
        raise ValueError("STRATUM_JOB_REQUIRED")
    if not session.authorized:
        raise StratumProtocolError("POOL_AUTHORIZATION_REQUIRED")
    if not session.current_job_id or job.job_id != session.current_job_id:
        raise StratumProtocolError("JOB_DOES_NOT_MATCH_CURRENT_SESSION")
    if job.job_id not in session.active_job_ids:
        raise StratumProtocolError("UNKNOWN_OR_STALE_JOB")
    if session.extranonce1_hex is None or session.extranonce2_size is None:
        raise StratumProtocolError("EXTRANONCE_NOT_NEGOTIATED")
    if not prevhash_dialect_confirmed:
        raise ValueError("STRATUM_PREVHASH_DIALECT_NOT_CONFIRMED")

    coinbase = build_coinbase(
        job, session.extranonce1_hex, extranonce2, session.extranonce2_size
    )
    merkle_root = merkle_root_from_coinbase(coinbase, job.merkle_branch_hex)
    candidate = build_header_candidate(
        version_hex=job.version_hex,
        prevhash_wire_hex=stratum_v1_prevhash_to_header_wire_hex(job.prevhash_hex),
        merkle_root_raw=merkle_root,
        ntime_hex=ntime_hex,
        nbits_hex=job.nbits_hex,
        nonce=int(nonce_hex, 16) if isinstance(nonce_hex, str)
        and len(nonce_hex) == 8
        and all(ch in "0123456789abcdefABCDEF" for ch in nonce_hex) else -1,
        share_target=share_target,
    )
    return {
        "evidence_class": "OFFLINE_SESSION_BOUND_HEADER_CANDIDATE",
        "job_id": job.job_id,
        "header_hex": candidate.header_bytes.hex(),
        "header_bytes": len(candidate.header_bytes),
        "nonce_hex": f"{candidate.nonce:08x}",
        "sha256d_display_hex": candidate.digest_display_hex,
        "hash_integer": candidate.hash_integer,
        "share_target": share_target,
        "meets_supplied_share_target": candidate.meets_share_target,
        "session_authorized": True,
        "job_current_for_session": True,
        "prevhash_dialect_confirmed_by_caller": True,
        "pool_submission_sent": False,
        "pool_acceptance_verified": False,
        "real_mining_verified": False,
        "revenue_verified": False,
    }
