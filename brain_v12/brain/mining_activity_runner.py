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


def benchmark_and_record_cpu_sha256d(
    *,
    activity_id: str,
    run_id: str,
    ledger: MiningActivityLedger,
    header_prefix: bytes,
    hashes_per_sample: int = 10_000,
    repeats: int = 3,
) -> tuple[dict, dict]:
    """Measure bounded host-CPU SHA256d throughput and persist it as unverified activity.

    header_prefix must be the first 76 bytes of an 80-byte Bitcoin header.
    This measures Python hashlib on the current CPU only; it is not an ASIC,
    pool hashrate, or profitability measurement.
    """
    import hashlib
    import statistics
    import time

    if not isinstance(header_prefix, bytes) or len(header_prefix) != 76:
        raise ValueError("HEADER_PREFIX_MUST_BE_76_BYTES")
    if isinstance(hashes_per_sample, bool) or not isinstance(hashes_per_sample, int) or not 1 <= hashes_per_sample <= 1_000_000:
        raise ValueError("HASHES_PER_SAMPLE_OUT_OF_RANGE")
    if isinstance(repeats, bool) or not isinstance(repeats, int) or not 1 <= repeats <= 5:
        raise ValueError("REPEATS_OUT_OF_RANGE")

    samples = []
    last_digest = ""
    for _ in range(repeats):
        start = time.perf_counter()
        for nonce in range(hashes_per_sample):
            first = hashlib.sha256(header_prefix + nonce.to_bytes(4, "little")).digest()
            last_digest = hashlib.sha256(first).hexdigest()
        elapsed = time.perf_counter() - start
        samples.append({
            "elapsed_seconds": elapsed,
            "hashes_per_second": hashes_per_sample / elapsed if elapsed > 0 else None,
        })
    rates = [sample["hashes_per_second"] for sample in samples if sample["hashes_per_second"] is not None]
    measurement = {
        "measurement": "python_hashlib_sha256d_header",
        "execution": "host_cpu_software",
        "hashes_per_sample": hashes_per_sample,
        "repeats": repeats,
        "samples": samples,
        "median_hashes_per_second": statistics.median(rates) if rates else None,
        "last_digest_hex": last_digest,
        "is_live_mining": False,
        "is_rtl_or_asic_measurement": False,
        "pool_contacted": False,
        "share_submitted": False,
    }
    activity = ledger.record(
        activity_id=activity_id,
        run_id=run_id,
        mode="SIMULATION",
        activity_type="HASHRATE_MEASUREMENT",
        source="brain_v12.brain.mining_activity_runner.host_cpu_software",
        evidence_ref=f"cpu-sha256d-benchmark:{run_id}",
        payload=measurement,
    )
    return measurement, activity
