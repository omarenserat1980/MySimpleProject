"""Deterministic SHA-256d mining-workload reference model.

This is an algorithmic workload model for exercising Brain's ASIC logic simulator
roadmap. It is NOT a gate-level SHA-256 circuit or a hardware-performance estimate.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class MiningWorkResult:
    algorithm: str
    nonce_start: int
    nonce_end_exclusive: int
    hashes_attempted: int
    target_hex: str
    solution_nonce: int | None
    solution_hash_hex: str | None
    found: bool
    measured_software_seconds: float
    model: str = "SHA256D_SOFTWARE_REFERENCE"
    hardware_measurement: bool = False
    hashrate_is_asic_estimate: bool = False


def sha256d(data: bytes) -> bytes:
    """Return Bitcoin-style double SHA-256 digest bytes."""
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def search_nonce(
    header_prefix: bytes,
    nonce_start: int,
    nonce_count: int,
    target: int,
    *,
    nonce_byteorder: str = "little",
) -> dict:
    """Search a bounded nonce interval for a SHA-256d digest <= target.

    header_prefix must be exactly 76 bytes (80-byte header without its nonce).
    The target is an integer in [0, 2**256-1]. This bounded function is intended
    for deterministic tests and workload experiments, not real mining revenue.
    """
    import time

    if not isinstance(header_prefix, bytes) or len(header_prefix) != 76:
        raise ValueError("HEADER_PREFIX_MUST_BE_76_BYTES")
    if isinstance(nonce_start, bool) or not isinstance(nonce_start, int) or not 0 <= nonce_start <= 0xFFFFFFFF:
        raise ValueError("NONCE_START_OUT_OF_RANGE")
    if isinstance(nonce_count, bool) or not isinstance(nonce_count, int) or not 1 <= nonce_count <= 1_000_000:
        raise ValueError("NONCE_COUNT_OUT_OF_RANGE")
    if nonce_start + nonce_count > 0x100000000:
        raise ValueError("NONCE_RANGE_OVERFLOWS_UINT32")
    if isinstance(target, bool) or not isinstance(target, int) or not 0 <= target < 2**256:
        raise ValueError("TARGET_OUT_OF_RANGE")
    if nonce_byteorder not in ("little", "big"):
        raise ValueError("INVALID_NONCE_BYTEORDER")

    started = time.perf_counter()
    found_nonce = None
    found_hash = None
    attempted = 0
    for nonce in range(nonce_start, nonce_start + nonce_count):
        header = header_prefix + nonce.to_bytes(4, nonce_byteorder)
        digest = sha256d(header)
        attempted += 1
        # Bitcoin proof-of-work compares the digest interpreted as a little-endian integer.
        if int.from_bytes(digest, "little") <= target:
            found_nonce = nonce
            found_hash = digest[::-1].hex()
            break
    elapsed = time.perf_counter() - started
    result = MiningWorkResult(
        algorithm="SHA-256d",
        nonce_start=nonce_start,
        nonce_end_exclusive=nonce_start + nonce_count,
        hashes_attempted=attempted,
        target_hex=f"{target:064x}",
        solution_nonce=found_nonce,
        solution_hash_hex=found_hash,
        found=found_nonce is not None,
        measured_software_seconds=elapsed,
    )
    return asdict(result)
