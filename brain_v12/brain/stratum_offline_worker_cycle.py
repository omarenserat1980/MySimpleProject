"""One bounded, offline Stratum worker cycle.

This composes the validated session, current job, bounded SHA256d search, and
share-request correlation into one testable unit. It intentionally performs no
network I/O, loads no credentials, and never claims live mining or revenue.
A separately reviewed TLS transport adapter is still required for live work.
"""
from __future__ import annotations

import json
from typing import Any

from .stratum_bounded_nonce_search import search_session_nonce_range
from .stratum_share_response_evidence import observe_share_response
from .stratum_v1_jobs import StratumJob
from .stratum_v1_protocol import StratumProtocolError, StratumV1Session


def run_offline_worker_cycle(
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
    """Search one bounded nonce range and prepare (but do not send) one share."""
    if not isinstance(session, StratumV1Session):
        raise StratumProtocolError("STRATUM_V1_SESSION_REQUIRED")
    if not isinstance(job, StratumJob):
        raise ValueError("VALIDATED_STRATUM_JOB_REQUIRED")
    if not session.authorized:
        raise StratumProtocolError("POOL_AUTHORIZATION_REQUIRED")
    if session.current_job_id != job.job_id or job.job_id not in session.active_job_ids:
        raise StratumProtocolError("UNKNOWN_OR_STALE_JOB")

    result = search_session_nonce_range(
        session,
        job,
        extranonce2=extranonce2,
        ntime_hex=ntime_hex,
        nonce_start=nonce_start,
        max_attempts=max_attempts,
        share_target=share_target,
        prevhash_dialect_confirmed=prevhash_dialect_confirmed,
    )
    base = {
        "evidence_class": "OFFLINE_STRATUM_WORKER_CYCLE",
        "job_id": job.job_id,
        "search": result,
        "transport_connected": False,
        "pool_submission_sent": False,
        "pool_acceptance_verified": False,
        "real_mining_verified": False,
        "revenue_verified": False,
    }
    if result["status"] != "LOCAL_TARGET_MATCH":
        return {**base, "status": "NO_CANDIDATE_IN_BOUNDED_RANGE", "submit_request": None}

    # Re-check freshness immediately before creating a submit request.
    if session.current_job_id != job.job_id or job.job_id not in session.active_job_ids:
        raise StratumProtocolError("UNKNOWN_OR_STALE_JOB")
    candidate = result["candidate"]
    wire = session.request_submit(
        job.job_id, extranonce2, ntime_hex, candidate["nonce_hex"]
    )
    request = json.loads(wire.decode("utf-8"))
    if request.get("method") != "mining.submit":
        raise AssertionError("SESSION_EMITTED_INVALID_SUBMISSION")
    return {
        **base,
        "status": "CANDIDATE_READY_FOR_TRANSPORT_NOT_SENT",
        "submit_request": request,
        "submit_wire_json": wire.decode("utf-8"),
        "pool_submission_sent": False,
        "pool_acceptance_verified": False,
        "real_mining_verified": False,
        "revenue_verified": False,
    }


def classify_offline_cycle_response(
    session: StratumV1Session, response_line: str | bytes
) -> dict[str, Any]:
    """Correlate a fixture or externally supplied response; not live proof."""
    outcome = observe_share_response(session, response_line)
    return {
        **outcome,
        "evidence_class": "OFFLINE_CYCLE_RESPONSE_CORRELATION",
        "live_transport_verified": False,
        "independent_share_validation_verified": False,
        "payout_verified": False,
        "revenue_verified": False,
    }
