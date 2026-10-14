"""Independent, dependency-free Bitcoin proof-of-work reference helpers.

This is a deterministic test oracle only. It does not connect to a node or pool,
fetch live chain data, mine profitably, or establish accepted shares/revenue.
"""
from __future__ import annotations

import hashlib
import struct


def sha256d(payload: bytes) -> bytes:
    """Return the raw 32-byte double-SHA-256 digest."""
    return hashlib.sha256(hashlib.sha256(payload).digest()).digest()


def _uint32_le(value: int, name: str) -> bytes:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 0xFFFFFFFF:
        raise ValueError(f"INVALID_{name.upper()}")
    return struct.pack("<I", value)


def _display_hash_to_wire(value: str, name: str) -> bytes:
    """Convert a 64-hex-character displayed hash to Bitcoin header wire order."""
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"INVALID_{name.upper()}_LENGTH")
    try:
        raw = bytes.fromhex(value)
    except ValueError as exc:
        raise ValueError(f"INVALID_{name.upper()}_HEX") from exc
    return raw[::-1]


def serialize_block_header(
    version: int,
    previous_block_hash: str,
    merkle_root: str,
    timestamp: int,
    bits: int,
    nonce: int,
) -> bytes:
    """Serialize the six fields of an 80-byte Bitcoin block header.

    Hash inputs use conventional displayed hex (big-endian text); they are
    reversed into the little-endian wire representation used by Bitcoin.
    """
    return b"".join((
        struct.pack("<i", _signed_int32(version)),
        _display_hash_to_wire(previous_block_hash, "PREVIOUS_BLOCK_HASH"),
        _display_hash_to_wire(merkle_root, "MERKLE_ROOT"),
        _uint32_le(timestamp, "TIMESTAMP"),
        _uint32_le(bits, "BITS"),
        _uint32_le(nonce, "NONCE"),
    ))


def _signed_int32(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not -(1 << 31) <= value < (1 << 31):
        raise ValueError("INVALID_VERSION")
    return value


def compact_bits_to_target(bits: int) -> int:
    """Decode Bitcoin's compact nBits target, rejecting negative/zero/overflow."""
    if not isinstance(bits, int) or isinstance(bits, bool) or not 0 <= bits <= 0xFFFFFFFF:
        raise ValueError("INVALID_BITS")
    exponent = bits >> 24
    mantissa = bits & 0x007FFFFF
    negative = bool(bits & 0x00800000)
    if negative or mantissa == 0:
        raise ValueError("INVALID_COMPACT_TARGET")
    if exponent <= 3:
        target = mantissa >> (8 * (3 - exponent))
    else:
        target = mantissa << (8 * (exponent - 3))
    if target <= 0 or target >= (1 << 256):
        raise ValueError("COMPACT_TARGET_OVERFLOW")
    return target


def check_proof_of_work(header: bytes, bits: int) -> dict[str, object]:
    """Check an 80-byte header against nBits; report deterministic facts only."""
    if not isinstance(header, bytes) or len(header) != 80:
        raise ValueError("INVALID_HEADER_LENGTH")
    target = compact_bits_to_target(bits)
    digest = sha256d(header)
    hash_value = int.from_bytes(digest, "little")
    return {
        "valid": hash_value <= target,
        "hash_display": digest[::-1].hex(),
        "target_hex": f"{target:064x}",
        "hash_value_le": hash_value,
        "target_value": target,
        "evidence_level": "LOCAL_REFERENCE_CHECK_ONLY",
        "live_mining": False,
        "pool_acceptance": False,
        "revenue_verified": False,
    }
