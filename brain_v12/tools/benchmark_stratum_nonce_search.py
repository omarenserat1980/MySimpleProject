"""Measure bounded local Stratum nonce-search throughput using synthetic data.

This tool does not connect to a pool, submit shares, or measure ASIC hardware.
Its output is a local software benchmark, not proof of accepted shares or revenue.
Run from the repository root:
    python -m brain_v12.tools.benchmark_stratum_nonce_search --attempts 1024
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from typing import Any

from brain_v12.brain.stratum_bounded_nonce_search import (
    MAX_NONCE_ATTEMPTS,
    search_session_nonce_range,
)
from brain_v12.brain.stratum_v1_jobs import StratumJob
from brain_v12.brain.stratum_v1_protocol import StratumV1Session


def synthetic_authorized_job() -> tuple[StratumV1Session, StratumJob]:
    """Create an in-memory authorized session and synthetic notify job."""
    session = StratumV1Session("benchmark.worker", "synthetic-only")
    session.request_subscribe()
    session.receive(json.dumps({"id": 1, "result": [[], "abcd", 2], "error": None}))
    session.request_authorize()
    session.receive(json.dumps({"id": 2, "result": True, "error": None}))
    params = [
        "benchmark-job", "00" * 32, "01020304", "aabbccdd", ["11" * 32],
        "20000000", "ffff001d", "65aa0000", True,
    ]
    session.receive(json.dumps({"method": "mining.notify", "params": params}))
    return session, StratumJob.from_notify(params)


def benchmark(attempts: int = 1024) -> dict[str, Any]:
    """Run one finite local benchmark and return measured, non-financial evidence."""
    if isinstance(attempts, bool) or not isinstance(attempts, int):
        raise ValueError("ATTEMPTS_MUST_BE_INTEGER")
    if not 1 <= attempts <= MAX_NONCE_ATTEMPTS:
        raise ValueError("ATTEMPTS_OUT_OF_RANGE")

    session, job = synthetic_authorized_job()
    started = time.perf_counter()
    result = search_session_nonce_range(
        session,
        job,
        extranonce2="c3d4",
        ntime_hex="65aa0000",
        nonce_start=0,
        max_attempts=attempts,
        share_target=1,
        prevhash_dialect_confirmed=True,
    )
    elapsed = time.perf_counter() - started
    checked = int(result["attempts"])
    return {
        "evidence_class": "LOCAL_SYNTHETIC_SOFTWARE_BENCHMARK",
        "status": result["status"],
        "requested_attempts": attempts,
        "attempts_checked": checked,
        "elapsed_seconds": elapsed,
        "hashes_per_second": checked / elapsed if elapsed > 0 else None,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "synthetic_job": True,
        "network_used": False,
        "pool_submission_sent": False,
        "pool_acceptance_verified": False,
        "asic_hashrate_verified": False,
        "real_mining_verified": False,
        "revenue_verified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempts", type=int, default=1024)
    args = parser.parse_args()
    try:
        print(json.dumps(benchmark(args.attempts), sort_keys=True, indent=2))
    except ValueError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
