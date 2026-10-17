"""Measured SHA-256d header-hashing benchmark for Electronic Brain.

This module benchmarks local CPU work only. It does not construct valid pool jobs,
connect to Stratum, validate Bitcoin proof-of-work targets, or earn BTC.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import platform
import time
from typing import Any

from .bitcoin_pow_reference import sha256d as reference_sha256d

HEADER_BYTES = 80
DEFAULT_HEADER = bytes(HEADER_BYTES)
IMPLEMENTATION_VERSION = "sha256d-benchmark-v2"


def sha256d(payload: bytes) -> bytes:
    """Return SHA256(SHA256(payload)) as raw digest bytes."""
    if not isinstance(payload, bytes):
        raise TypeError("PAYLOAD_MUST_BE_BYTES")
    return hashlib.sha256(hashlib.sha256(payload).digest()).digest()


def benchmark_header_hashing(
    *, duration_seconds: float = 1.0, max_hashes: int = 100_000,
    header: bytes = DEFAULT_HEADER,
) -> dict[str, Any]:
    """Measure bounded local SHA-256d throughput and report evidence provenance.

    The 32-bit nonce field is changed per attempt. Bounds are deliberately small
    to protect mobile devices and API callers from unbounded CPU use. A reference
    comparison is performed on the last completed candidate; this is a local
    software benchmark, never proof of pool acceptance or physical ASIC presence.
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
    started_at = datetime.now(timezone.utc).isoformat()
    start = time.perf_counter()
    deadline = start + float(duration_seconds)
    count = 0
    last_digest = b""
    last_payload = b""
    while count < max_hashes and time.perf_counter() < deadline:
        work[76:80] = count.to_bytes(4, "little")
        last_payload = bytes(work)
        last_digest = sha256d(last_payload)
        count += 1
    elapsed = time.perf_counter() - start

    # Do not claim verification or a usable rate if no operation completed or
    # elapsed time is invalid. The independent reference is checked on the final
    # actual input, not on synthetic hard-coded timing data.
    verification_result = (
        "MATCH" if count > 0 and reference_sha256d(last_payload) == last_digest
        else "NO_COMPLETED_HASH" if count == 0
        else "MISMATCH"
    )
    valid_measurement = count > 0 and elapsed > 0 and verification_result == "MATCH"
    resource_identity = {
        "runtime": platform.python_implementation(),
        "python_version": platform.python_version(),
        "os": platform.system(),
        "architecture": platform.machine(),
        "host_identity": "NOT_ATTESTED",
    }
    return {
        "ok": valid_measurement,
        "mode": "LOCAL_BENCHMARK_ONLY",
        "execution_mode": "CPU_SOFTWARE",
        "algorithm": "SHA-256d",
        "implementation_version": IMPLEMENTATION_VERSION,
        "worker_id": "local-process-unidentified",
        "started_at": started_at,
        "header_bytes": HEADER_BYTES,
        "hashes_completed": count,
        "elapsed_seconds": elapsed,
        "hashrate_hps": count / elapsed if valid_measurement else None,
        "hashrate_hs": round(count / elapsed, 3) if valid_measurement else None,
        "last_digest_hex": last_digest.hex() if count else None,
        "verification_result": verification_result,
        "resource_identity": resource_identity,
        "evidence_status": "SOFTWARE_BENCHMARK_VERIFIED" if valid_measurement else "IMPLEMENTED_UNVERIFIED",
        "nonce_field": "little_endian_uint32",
        "target_checked": False,
        "pool_connected": False,
        "shares_submitted": 0,
        "real_bitcoin_mining": False,
        "revenue_verified": False,
        "limitations": [
            "This benchmark hashes a synthetic header; it is not a valid pool job.",
            "Only the last completed digest is compared with the reference helper.",
            "No Bitcoin proof-of-work target is checked.",
            "No ASIC or GPU throughput is inferred from this CPU measurement.",
            "The execution host identity is not attested by this utility.",
        ],
    }
