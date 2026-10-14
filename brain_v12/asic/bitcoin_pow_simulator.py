"""Bounded, offline Bitcoin-style proof-of-work simulator.

This is a deterministic software test tool, not a production miner. It never
contacts a pool, wallet, node, or network service. The caller must supply an
80-byte candidate header and a target. Work is bounded by max_attempts.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any


HEADER_SIZE = 80
NONCE_OFFSET = 76
MAX_NONCE = (1 << 32) - 1
MAX_ATTEMPTS = 1_000_000


@dataclass(frozen=True)
class PowSimulationResult:
    found: bool
    nonce: int | None
    attempts: int
    hash_hex: str | None
    hash_value: int | None
    target: int
    status: str
    live_mining: bool = False
    pool_connected: bool = False
    revenue_verified: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "found": self.found,
            "nonce": self.nonce,
            "attempts": self.attempts,
            "hash_hex": self.hash_hex,
            "hash_value": self.hash_value,
            "target": self.target,
            "status": self.status,
            "live_mining": self.live_mining,
            "pool_connected": self.pool_connected,
            "revenue_verified": self.revenue_verified,
            "evidence_scope": "BOUNDED_OFFLINE_SOFTWARE_SIMULATION",
        }


def sha256d(data: bytes) -> bytes:
    """Return SHA256(SHA256(data)); no network or external state."""
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def simulate_pow(
    header: bytes,
    target: int,
    *,
    start_nonce: int = 0,
    max_attempts: int = 1_000,
) -> PowSimulationResult:
    """Search a bounded nonce range for an 80-byte header meeting target.

    Bitcoin interprets the displayed block hash as a little-endian integer.
    This helper overwrites the header's 4-byte nonce at byte offset 76.
    max_attempts is capped to avoid unbounded CI or accidental mining workloads.
    """
    if not isinstance(header, bytes) or len(header) != HEADER_SIZE:
        raise ValueError("HEADER_MUST_BE_EXACTLY_80_BYTES")
    if isinstance(target, bool) or not isinstance(target, int) or not 0 <= target < (1 << 256):
        raise ValueError("TARGET_MUST_BE_A_256_BIT_UNSIGNED_INTEGER")
    if isinstance(start_nonce, bool) or not isinstance(start_nonce, int) or not 0 <= start_nonce <= MAX_NONCE:
        raise ValueError("START_NONCE_OUT_OF_RANGE")
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or not 1 <= max_attempts <= MAX_ATTEMPTS:
        raise ValueError("MAX_ATTEMPTS_MUST_BE_BETWEEN_1_AND_1000000")
    attempts_allowed = min(max_attempts, MAX_NONCE - start_nonce + 1)
    for offset in range(attempts_allowed):
        nonce = start_nonce + offset
        candidate = bytearray(header)
        candidate[NONCE_OFFSET:NONCE_OFFSET + 4] = nonce.to_bytes(4, "little")
        digest = sha256d(bytes(candidate))
        value = int.from_bytes(digest, "little")
        if value <= target:
            return PowSimulationResult(
                True, nonce, offset + 1, digest[::-1].hex(), value, target, "SIMULATED_TARGET_MET"
            )
    return PowSimulationResult(
        False, None, attempts_allowed, None, None, target, "SIMULATION_LIMIT_REACHED"
    )
