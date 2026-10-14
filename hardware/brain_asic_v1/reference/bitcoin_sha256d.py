"""Independent software reference for Bitcoin's 80-byte block header.

This is a correctness oracle for RTL verification, not an ASIC or miner.
"""
from __future__ import annotations
import hashlib


def sha256d(data: bytes) -> bytes:
    """Return Bitcoin-style double SHA-256 digest bytes."""
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def header_hash(header: bytes) -> str:
    """Return the conventional displayed Bitcoin block hash."""
    if len(header) != 80:
        raise ValueError("Bitcoin block header must be exactly 80 bytes")
    return sha256d(header)[::-1].hex()


def meets_target(header: bytes, target: int) -> bool:
    """Check proof of work using Bitcoin's little-endian digest integer."""
    if len(header) != 80:
        raise ValueError("Bitcoin block header must be exactly 80 bytes")
    if not 0 <= target < (1 << 256):
        raise ValueError("target must be a 256-bit unsigned integer")
    return int.from_bytes(sha256d(header), "little") <= target
