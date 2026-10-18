"""One bounded offline Stratum cycle bound to an explicit pool difficulty.

This wrapper derives a conventional SHA256d share target from the supplied
session difficulty and passes that target into the existing offline cycle.
The caller is responsible for sourcing difficulty from the authenticated
session's current mining.set_difficulty notification. This module performs no
network I/O and never claims live mining, accepted shares, or revenue.
"""
from __future__ import annotations

from typing import Any

from .stratum_difficulty_target import share_target_from_difficulty
from .stratum_offline_worker_cycle import run_offline_worker_cycle
from .stratum_v1_jobs import StratumJob
from .stratum_v1_protocol import StratumV1Session


def run_difficulty_bound_offline_cycle(
    session: StratumV1Session,
    job: StratumJob,
    *,
    pool_reported_difficulty: Any,
    extranonce2: str,
    ntime_hex: str,
    nonce_start: int,
    max_attempts: int,
    prevhash_dialect_confirmed: bool = False,
) -> dict[str, Any]:
    """Run a bounded offline search using the supplied pool difficulty.

    The difficulty must be the current value reported by the authenticated
    Stratum V1 session; this pure function cannot verify its provenance.
    """
    target_evidence = share_target_from_difficulty(pool_reported_difficulty)
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
        "evidence_class": "OFFLINE_DIFFICULTY_BOUND_STRATUM_WORKER_CYCLE",
        "difficulty_target": target_evidence,
        "difficulty_bound_to_current_session_by_this_function": False,
        "pool_difficulty_provenance_verified": False,
        "transport_connected": False,
        "pool_submission_sent": False,
        "pool_acceptance_verified": False,
        "real_mining_verified": False,
        "revenue_verified": False,
    }
