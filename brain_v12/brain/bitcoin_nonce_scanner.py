"""Bounded offline Bitcoin header nonce scanner.

This is a CPU test primitive, not a Stratum client or a production miner.
It performs no networking, credential access, persistence, or pool submission.
"""
from __future__ import annotations

from brain_v12.brain.bitcoin_header import sha256d


MAX_NONCE_ATTEMPTS = 1_000_000


def scan_nonce(
    header_prefix: bytes,
    share_target: int,
    *,
    start_nonce: int = 0,
    max_attempts: int = 1_000,
) -> dict[str, object]:
    """Scan a bounded nonce range for an 80-byte Bitcoin header candidate.

    header_prefix must be the first 76 serialized header bytes. The nonce is
    appended as a 4-byte little-endian integer. Hash comparison uses Bitcoin's
    little-endian numeric interpretation of SHA256d. A match only means the
    candidate meets the supplied target; it does not prove pool acceptance.
    """
    if not isinstance(header_prefix, bytes) or len(header_prefix) != 76:
        raise ValueError("HEADER_PREFIX_MUST_BE_76_BYTES")
    if isinstance(share_target, bool) or not isinstance(share_target, int) or not 0 < share_target < 2**256:
        raise ValueError("SHARE_TARGET_OUT_OF_RANGE")
    if isinstance(start_nonce, bool) or not isinstance(start_nonce, int) or not 0 <= start_nonce <= 0xFFFFFFFF:
        raise ValueError("START_NONCE_OUT_OF_RANGE")
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or not 1 <= max_attempts <= MAX_NONCE_ATTEMPTS:
        raise ValueError("MAX_ATTEMPTS_OUT_OF_RANGE")
    attempts = min(max_attempts, 0x100000000 - start_nonce)
    for offset in range(attempts):
        nonce = start_nonce + offset
        header = header_prefix + nonce.to_bytes(4, "little")
        digest = sha256d(header)
        hash_integer = int.from_bytes(digest, "little")
        if hash_integer <= share_target:
            return {
                "found": True,
                "nonce": nonce,
                "header_hex": header.hex(),
                "hash_display_hex": digest[::-1].hex(),
                "hash_integer": hash_integer,
                "attempts": offset + 1,
                "meets_supplied_target": True,
                "pool_share_acceptance_verified": False,
                "mode": "OFFLINE_CPU_TEST",
            }
    return {
        "found": False,
        "nonce": None,
        "header_hex": None,
        "hash_display_hex": None,
        "hash_integer": None,
        "attempts": attempts,
        "meets_supplied_target": False,
        "pool_share_acceptance_verified": False,
        "mode": "OFFLINE_CPU_TEST",
    }
