"""Bitcoin header and Stratum difficulty helpers with explicit endian contracts.

These functions are deterministic building blocks only. They do not connect to
a pool, mine, or assert that a pool share has been accepted.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib


def _fixed_hex(value: str, field: str, size: int) -> bytes:
    if not isinstance(value, str) or len(value) != size * 2:
        raise ValueError("INVALID_" + field.upper() + "_WIDTH")
    # bytes.fromhex() accepts embedded ASCII whitespace. Protocol fields must
    # be contiguous hexadecimal characters; reject non-canonical spellings.
    if any(char not in "0123456789abcdefABCDEF" for char in value):
        raise ValueError("INVALID_" + field.upper() + "_HEX")
    decoded = bytes.fromhex(value)
    if len(decoded) != size:
        raise ValueError("INVALID_" + field.upper() + "_WIDTH")
    return decoded


def sha256d(data: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def stratum_v1_prevhash_to_header_wire_hex(prevhash_hex: str) -> str:
    """Normalize the common legacy Stratum V1 prevhash encoding.

    The legacy mining.notify prevhash encoding is eight little-endian 32-bit
    words. Convert each 4-byte word to the byte order serialized in a Bitcoin
    block header. This is NOT a whole-32-byte reversal. The caller must use this
    only when the pool's documented/proven dialect matches this convention.
    The function does not contact a pool or infer a dialect.
    """
    raw = _fixed_hex(prevhash_hex, "stratum_v1_prevhash", 32)
    return b"".join(raw[i:i + 4][::-1] for i in range(0, 32, 4)).hex()


@dataclass(frozen=True)
class HeaderCandidate:
    header_bytes: bytes
    nonce: int
    digest_display_hex: str
    hash_integer: int
    meets_share_target: bool


def build_header_candidate(
    *,
    version_hex: str,
    prevhash_wire_hex: str,
    merkle_root_raw: bytes,
    ntime_hex: str,
    nbits_hex: str,
    nonce: int,
    share_target: int,
) -> HeaderCandidate:
    """Build an 80-byte header from explicitly serialized fields.

    prevhash_wire_hex is the 32-byte previous hash in wire/header byte order;
    merkle_root_raw is the raw 32-byte SHA256d accumulator from this module.
    This explicit contract avoids guessing a pool's byte order. Verify against
    known vectors and the chosen pool's documented protocol before live use.
    """
    version = _fixed_hex(version_hex, "version", 4)
    prevhash = _fixed_hex(prevhash_wire_hex, "prevhash_wire", 32)
    ntime = _fixed_hex(ntime_hex, "ntime", 4)
    nbits = _fixed_hex(nbits_hex, "nbits", 4)
    if not isinstance(merkle_root_raw, bytes) or len(merkle_root_raw) != 32:
        raise ValueError("INVALID_MERKLE_ROOT")
    if isinstance(nonce, bool) or not isinstance(nonce, int) or not 0 <= nonce <= 0xFFFFFFFF:
        raise ValueError("NONCE_OUT_OF_RANGE")
    if isinstance(share_target, bool) or not isinstance(share_target, int) or not 0 < share_target < 2**256:
        raise ValueError("SHARE_TARGET_OUT_OF_RANGE")
    header = version + prevhash + merkle_root_raw + ntime + nbits + nonce.to_bytes(4, "little")
    if len(header) != 80:
        raise AssertionError("INTERNAL_HEADER_SIZE_ERROR")
    digest = sha256d(header)
    hash_int = int.from_bytes(digest, "little")
    return HeaderCandidate(header, nonce, digest[::-1].hex(), hash_int, hash_int <= share_target)


# Bitcoin's conventional difficulty-1 target used by Stratum V1 pools.
# Pool-specific difficulty conventions must be confirmed before live submission.
STRATUM_DIFFICULTY_ONE_TARGET = 0x00000000FFFF0000000000000000000000000000000000000000000000000000


def stratum_difficulty_to_share_target(difficulty: int | float | str | Decimal) -> int:
    """Convert conventional Stratum V1 difficulty to an integer share target.

    Uses Decimal(str(value)) to avoid introducing additional binary-float
    rounding. The convention is target = floor(diff1_target / difficulty).
    This helper does not infer a pool dialect or prove that a pool uses this
    difficulty-1 target; callers must confirm that independently.
    """
    if isinstance(difficulty, bool) or not isinstance(difficulty, (int, float, str, Decimal)):
        raise ValueError("INVALID_STRATUM_DIFFICULTY")
    try:
        value = Decimal(str(difficulty))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("INVALID_STRATUM_DIFFICULTY") from exc
    if not value.is_finite() or value <= 0:
        raise ValueError("INVALID_STRATUM_DIFFICULTY")
    target = int(Decimal(STRATUM_DIFFICULTY_ONE_TARGET) / value)
    if not 0 < target < 2**256:
        raise ValueError("STRATUM_DIFFICULTY_TARGET_OUT_OF_RANGE")
    return target


def compact_nbits_to_target(nbits_hex: str) -> int:
    """Decode Bitcoin compact target (nBits serialized as four little-endian bytes)."""
    raw = _fixed_hex(nbits_hex, "nbits", 4)
    compact = int.from_bytes(raw, "little")
    exponent = compact >> 24
    mantissa = compact & 0x007FFFFF
    negative = bool(compact & 0x00800000)
    if negative or mantissa == 0 or exponent > 32:
        raise ValueError("INVALID_COMPACT_TARGET")

    # Bitcoin SetCompact semantics: for exponents <= 3 the mantissa is shifted
    # right; smaller exponents are not automatically invalid. The resulting
    # target must still be non-zero and fit in 256 bits.
    if exponent <= 3:
        target = mantissa >> (8 * (3 - exponent))
    else:
        target = mantissa << (8 * (exponent - 3))
    if not 0 < target < 2**256:
        raise ValueError("COMPACT_TARGET_OUT_OF_RANGE")
    return target


def verify_candidate_against_target(header: bytes, target: int) -> dict[str, object]:
    if not isinstance(header, bytes) or len(header) != 80:
        raise ValueError("BITCOIN_HEADER_MUST_BE_80_BYTES")
    if isinstance(target, bool) or not isinstance(target, int) or not 0 < target < 2**256:
        raise ValueError("TARGET_OUT_OF_RANGE")
    digest = sha256d(header)
    value = int.from_bytes(digest, "little")
    return {
        "header_sha256d_display_hex": digest[::-1].hex(),
        "hash_integer_meets_target": value <= target,
        "hash_integer": value,
        "target": target,
        "pool_share_acceptance_verified": False,
    }
