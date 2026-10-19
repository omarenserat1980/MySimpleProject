"""Run bounded SHA256d work and persist its observed result as simulation activity.

This adapter is an explicit call boundary: it never starts itself, opens a network
connection, submits shares, or recognizes revenue. Results are persisted even when
the search finds no nonce, times out, or is cancelled.
"""
from __future__ import annotations

from typing import Callable

from brain_v12.business.mining_activity_ledger import MiningActivityLedger
from brain_v12.brain.bounded_pow_task_engine import PowTaskResult, run_bounded_pow_task


def run_and_record_pow_task(
    header: bytes,
    target: int,
    *,
    activity_id: str,
    run_id: str,
    ledger: MiningActivityLedger,
    start_nonce: int = 0,
    max_total_hashes: int = 100_000,
    batch_hashes: int = 1_000,
    timeout_seconds: float = 30.0,
    cancel_requested: Callable[[], bool] | None = None,
) -> tuple[PowTaskResult, dict]:
    """Execute one bounded offline task, then persist what it actually observed."""
    result = run_bounded_pow_task(
        header, target, start_nonce=start_nonce,
        max_total_hashes=max_total_hashes, batch_hashes=batch_hashes,
        timeout_seconds=timeout_seconds, cancel_requested=cancel_requested,
    )
    activity = ledger.record(
        activity_id=activity_id,
        run_id=run_id,
        mode="SIMULATION",
        activity_type="SHA256D_RESULT",
        source="brain_v12.brain.mining_activity_runner",
        evidence_ref=f"pow-task:{run_id}",
        payload={
            "status": result.status,
            "start_nonce": result.start_nonce,
            "next_nonce": result.next_nonce,
            "hashes_checked": result.hashes_checked,
            "nonce": result.nonce,
            "hash_hex": result.hash_hex,
            "pool_contacted": result.pool_contacted,
            "share_submitted": result.share_submitted,
            "pool_acceptance_verified": result.pool_acceptance_verified,
            "revenue_verified": result.revenue_verified,
        },
    )
    return result, activity
