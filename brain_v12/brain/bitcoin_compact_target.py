"""Strict Bitcoin compact nBits target decoding, without mining side effects."""
from __future__ import annotations

UINT32_MAX = 0xFFFFFFFF
MAX_TARGET = (1 << 256) - 1


def compact_bits_to_target(compact: int) -> int:
    """Decode Bitcoin's compact nBits representation into a positive uint256 target.

    Rejects negative, zero, overflowed, malformed and out-of-range targets.
    This is a numeric conversion only; it does not establish a pool share target
    or network consensus context.
    """
    if isinstance(compact, bool) or not isinstance(compact, int) or not 0 <= compact <= UINT32_MAX:
        raise ValueError("COMPACT_BITS_OUT_OF_RANGE")
    size = compact >> 24
    word = compact & 0x007FFFFF
    negative = word != 0 and (compact & 0x00800000) != 0
    overflow = word != 0 and (
        size > 34 or (word > 0xFF and size > 33) or (word > 0xFFFF and size > 32)
    )
    if negative:
        raise ValueError("NEGATIVE_COMPACT_TARGET")
    if overflow:
        raise ValueError("COMPACT_TARGET_OVERFLOW")
    if size <= 3:
        target = word >> (8 * (3 - size))
    else:
        target = word << (8 * (size - 3))
    if target <= 0:
        raise ValueError("ZERO_COMPACT_TARGET")
    if target > MAX_TARGET:
        raise ValueError("COMPACT_TARGET_OVERFLOW")
    return target


def target_to_compact_bits(target: int) -> int:
    """Encode a positive uint256 target using Bitcoin's compact nBits format."""
    if isinstance(target, bool) or not isinstance(target, int) or not 0 < target <= MAX_TARGET:
        raise ValueError("TARGET_OUT_OF_RANGE")
    size = (target.bit_length() + 7) // 8
    if size <= 3:
        compact = target << (8 * (3 - size))
    else:
        compact = target >> (8 * (size - 3))
    compact &= 0xFFFFFF
    if compact & 0x00800000:
        compact >>= 8
        size += 1
    compact |= size << 24
    return compact
