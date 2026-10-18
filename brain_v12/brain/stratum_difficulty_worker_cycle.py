"""One bounded offline Stratum cycle bound to the session's current difficulty.

Difficulty is read from StratumV1Session after its protocol parser accepts a
mining.set_difficulty notification. Callers cannot pass an unrelated target or
difficulty. This remains offline-only: no network I/O, share submission, or
claim of live mining or revenue.
"""
from __future__ import annotations

from .stratum_difficulty_target import share_target_from_difficulty
from .stratum_offline_worker_cycle import run_offline_worker_cycle
from .stratum_v1_jobs import StratumJob
from .stratum_v1_protocol import StratumProtocolError, StratumV1Session


def run_difficulty_bound_offline_cycle(
    session: StratumV1Session,
    job: StratumJob,
    *,
    extranonce2: str,
    ntime_hex: str,
    nonce_start: int,
    max_attempts: int,
    prevhash_dialect_confirmed: bool = False,
) -> dict[str, object]:
    """Search using only the difficulty stored by the validated session."""
    if not isinstance(session, StratumV1Session):
        raise StratumProtocolError("STRATUM_V1_SESSION_REQUIRED")
    if session.difficulty is None:
        raise StratumProtocolError("SESSION_DIFFICULTY_REQUIRED")
    target_evidence = share_target_from_difficulty(session.difficulty)
    cycle = run_offline_worker_cycle(
        session,
        job,
        extranonce2=extranonce2,
        ntime_hex=ntime_hex,
        nonce_start=nonce_start,
        max_attempts=max_attempts,
        share_target=target_evidence["share_target"],
        prevhash_dialect_confirmed=prevhash_dialect_confirmed,
    )
    return {
        **cycle,
        "evidence_class": "OFFLINE_SESSION_DIFFICULTY_BOUND_STRATUM_WORKER_CYCLE",
        "difficulty_target": target_evidence,
        "difficulty_bound_to_validated_session_state": True,
        "difficulty_provenance_independently_verified": False,
        "transport_connected": False,
        "pool_submission_sent": False,
        "pool_acceptance_verified": False,
        "real_mining_verified": False,
        "revenue_verified": False,
    }
