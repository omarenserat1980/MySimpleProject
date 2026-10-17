"""Strict Bitcoin 80-byte header assembly from already-normalized fields.

This module deliberately does not interpret Stratum V1 byte order. Pool-specific
prevhash and merkle-branch normalization must be implemented and tested against
a documented pool convention before calling this function. No networking,
credentials, nonce search, or share submission occurs here.
"""
from __future__ import annotations

from brain_v12.brain.brain_owned_compute_runtime import validate_header


def _four_bytes(value: bytes, field: str) -> bytes:
    if not isinstance(value, bytes) or len(value) != 4:
        raise ValueError(f"{field}_MUST_BE_4_BYTES")
    return value


def _hash_bytes(value: bytes, field: str) -> bytes:
    if not isinstance(value, bytes) or len(value) != 32:
        raise ValueError(f"{field}_MUST_BE_32_BYTES")
    return value


def build_normalized_header(
    *,
    version_le: bytes,
    prevhash_header_bytes: bytes,
    merkle_root_header_bytes: bytes,
    ntime_le: bytes,
    nbits_le: bytes,
    nonce: int,
) -> bytes:
    """Assemble an 80-byte header from fields already encoded for header wire order.

    version_le, ntime_le, and nbits_le must each be the exact four bytes that
    belong in the serialized Bitcoin header. prevhash_header_bytes and
    merkle_root_header_bytes must already use serialized header byte order.
    The nonce is encoded as a uint32 little-endian integer.
    """
    version = _four_bytes(version_le, "VERSION")
    prevhash = _hash_bytes(prevhash_header_bytes, "PREVHASH_HEADER_BYTES")
    merkle_root = _hash_bytes(merkle_root_header_bytes, "MERKLE_ROOT_HEADER_BYTES")
    ntime = _four_bytes(ntime_le, "NTIME")
    nbits = _four_bytes(nbits_le, "NBITS")
    if isinstance(nonce, bool) or not isinstance(nonce, int) or not 0 <= nonce <= 0xFFFFFFFF:
        raise ValueError("NONCE_OUT_OF_RANGE")

    header = (
        version + prevhash + merkle_root + ntime + nbits
        + nonce.to_bytes(4, "little")
    )
    validate_header(header)
    return header
