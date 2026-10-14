"""Real CPU SHA-256d worker primitive for Bitcoin mining experiments.

This performs genuine double-SHA-256 over 80-byte Bitcoin block headers.
It does not connect to a pool, submit shares, hold a wallet, or claim revenue.
The caller must supply an authorized work header template and nonce range.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class SHA256WorkResult:
    nonces_tested: int
    elapsed_seconds: float
    hashes_per_second: float
    matching_nonce: int | None
    matching_hash_hex: str | None


def double_sha256(header: bytes) -> bytes:
    if len(header) != 80:
        raise ValueError("bitcoin_block_header_must_be_80_bytes")
    return hashlib.sha256(hashlib.sha256(header).digest()).digest()


def scan_nonce_range(
    header_prefix: bytes,
    *,
    start_nonce: int,
    end_nonce: int,
    target: int,
    max_seconds: float | None = None,
) -> SHA256WorkResult:
    """Perform genuine SHA-256d work over a nonce interval.

    header_prefix must be the first 76 bytes of a Bitcoin block header.
    target is the numeric proof-of-work target interpreted from the resulting
    digest in Bitcoin's conventional little-endian comparison.
    """
    import time

    if len(header_prefix) != 76:
        raise ValueError("header_prefix_must_be_76_bytes")
    if not 0 <= start_nonce <= 0xFFFFFFFF:
        raise ValueError("invalid_start_nonce")
    if not 0 <= end_nonce <= 0xFFFFFFFF or end_nonce < start_nonce:
        raise ValueError("invalid_end_nonce")
    if target < 0 or target > (1 << 256) - 1:
        raise ValueError("invalid_target")

    started = time.perf_counter()
    tested = 0
    found_nonce = None
    found_hash = None

    for nonce in range(start_nonce, end_nonce + 1):
        header = header_prefix + nonce.to_bytes(4, "little")
        digest = double_sha256(header)
        tested += 1
        if int.from_bytes(digest, "little") <= target:
            found_nonce = nonce
            found_hash = digest.hex()
            break
        if max_seconds is not None and time.perf_counter() - started >= max_seconds:
            break

    elapsed = max(time.perf_counter() - started, 1e-12)
    return SHA256WorkResult(
        nonces_tested=tested,
        elapsed_seconds=elapsed,
        hashes_per_second=tested / elapsed,
        matching_nonce=found_nonce,
        matching_hash_hex=found_hash,
    )
