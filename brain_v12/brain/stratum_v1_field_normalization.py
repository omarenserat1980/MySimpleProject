"""Explicit, pool-neutral Stratum V1 hex-to-header field conversions.

This module only handles unambiguous field encodings. It does not normalize
prevhash, because pools/implementations can differ in how that field is
presented. Callers must supply an already-resolved prevhash byte sequence to
the normalized header builder, validated against a known pool vector.
"""
from __future__ import annotations
import re

_HEX = re.compile(r"^[0-9a-fA-F]+$")


def _decode_hex(value: str, field: str, expected_bytes: int) -> bytes:
    if not isinstance(value, str) or len(value) != expected_bytes * 2 or not _HEX.fullmatch(value):
        raise ValueError(f"INVALID_{field.upper()}_HEX")
    return bytes.fromhex(value)


def stratum_u32_to_header_bytes(value: str, *, field: str) -> bytes:
    """Convert a fixed-width Stratum uint32 hex field into header little-endian bytes.

    The input must be exactly eight hex characters. This helper is intended for
    fields such as version, ntime, and nbits whose numeric encoding is reversed
    when serialized into a Bitcoin block header.
    """
    if not isinstance(field, str) or field not in {"version", "ntime", "nbits", "nonce"}:
        raise ValueError("UNSUPPORTED_U32_FIELD")
    return _decode_hex(value, field, 4)[::-1]


def decode_hash32_hex(value: str, *, reverse_bytes: bool) -> bytes:
    """Decode a 32-byte hash with an explicit caller-selected byte reversal.

    `reverse_bytes` is mandatory so no pool-specific hash order is guessed.
    This does not perform Stratum's possible word-level prevhash transforms.
    """
    if not isinstance(reverse_bytes, bool):
        raise ValueError("REVERSE_BYTES_MUST_BE_BOOLEAN")
    decoded = _decode_hex(value, "hash32", 32)
    return decoded[::-1] if reverse_bytes else decoded


def decode_merkle_branch_hex(value: str) -> bytes:
    """Decode one Stratum merkle branch without silently changing byte order."""
    return _decode_hex(value, "merkle_branch", 32)
