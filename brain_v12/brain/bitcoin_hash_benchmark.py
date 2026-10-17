"""Measured SHA-256d header-hashing benchmark for Electronic Brain.

This module benchmarks local CPU work only. It does not construct valid pool jobs,
connect to Stratum, validate Bitcoin proof-of-work targets, or earn BTC.
"""
from __future__ import annotations

import hashlib
import time
from typing import Any


HEADER_BYTES = 80
DEFAULT_HEADER = bytes(HEADER_BYTES)


def sha256d(payload: bytes) -> bytes:
    """Return SHA256(SHA256(payload)) as raw digest bytes."""
    if not isinstance(payload, bytes):
        raise TypeError("PAYLOAD_MUST_BE_BYTES")
    return hashlib.sha256(hashlib.sha256(payload).digest()).digest()


def benchmark_header_hashing(
    *, duration_seconds: float = 1.0, max_hashes: int = 100_000,
    header: bytes = DEFAULT_HEADER,
) -> dict[str, Any]:
    """Measure repeatable local SHA-256d throughput over an 80-byte header.

    The 32-bit nonce field is changed per attempt. Bounds are deliberately small
    to protect mobile devices and API callers from unbounded CPU use.
    """
    if not isinstance(header, bytes) or len(header) != HEADER_BYTES:
        raise ValueError("HEADER_MUST_BE_EXACTLY_80_BYTES")
    if isinstance(duration_seconds, bool) or not isinstance(duration_seconds, (int, float)):
        raise ValueError("INVALID_DURATION")
    if not 0.05 <= float(duration_seconds) <= 3.0:
        raise ValueError("DURATION_OUT_OF_RANGE_0_05_TO_3_SECONDS")
    if isinstance(max_hashes, bool) or not isinstance(max_hashes, int) or not 1 <= max_hashes <= 100_000:
        raise ValueError("MAX_HASHES_OUT_OF_RANGE_1_TO_100000")

    work = bytearray(header)
    start = time.perf_counter()
    deadline = start + float(duration_seconds)
    count = 0
    last_digest = b""
    while count < max_hashes and time.perf_counter() < deadline:
        work[76:80] = count.to_bytes(4, "little")
        last_digest = sha256d(bytes(work))
        count += 1
    elapsed = max(time.perf_counter() - start, 1e-12)
    return {
        "ok": True,
        "mode": "LOCAL_BENCHMARK_ONLY",
        "algorithm": "SHA-256d",
        "header_bytes": HEADER_BYTES,
        "hashes_completed": count,
        "elapsed_seconds": round(elapsed, 6),
        "hashrate_hs": round(count / elapsed, 3),
        "last_digest_hex": last_digest.hex(),
        "nonce_field": "little_endian_uint32",
        "target_checked": False,
        "pool_connected": False,
        "shares_submitted": 0,
        "real_bitcoin_mining": False,
        "revenue_verified": False,
        "limitations": [
            "This benchmark hashes a synthetic header; it is not a valid pool job.",
            "No Bitcoin proof-of-work target is checked.",
            "No ASIC or GPU throughput is inferred from this CPU measurement.",
        ],
    }
