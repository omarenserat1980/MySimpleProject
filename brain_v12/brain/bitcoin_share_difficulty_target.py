"""Explicit difficulty-to-target conversion for Bitcoin-style share targets."""
from __future__ import annotations
from decimal import Decimal, InvalidOperation, ROUND_FLOOR, localcontext
import math
from typing import SupportsInt

MAX_TARGET = (1 << 256) - 1


def difficulty_to_target(difficulty: int | float | str, *, difficulty_one_target: int) -> int:
    """Compute floor(difficulty_one_target / difficulty) without implicit clamping.

    The caller must provide the correct difficulty-one baseline for the pool's
    documented convention. This helper does not infer pool vardiff semantics,
    block target, network, or share acceptance. It performs no mining/network I/O.
    """
    if (isinstance(difficulty_one_target, bool) or not isinstance(difficulty_one_target, int)
            or not 0 < difficulty_one_target <= MAX_TARGET):
        raise ValueError("DIFFICULTY_ONE_TARGET_OUT_OF_RANGE")
    if isinstance(difficulty, bool) or not isinstance(difficulty, (int, float, str)):
        raise ValueError("DIFFICULTY_MUST_BE_NUMERIC")
    if isinstance(difficulty, float) and not math.isfinite(difficulty):
        raise ValueError("DIFFICULTY_MUST_BE_FINITE")
    try:
        value = Decimal(str(difficulty))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("INVALID_DIFFICULTY") from exc
    if not value.is_finite() or value <= 0:
        raise ValueError("DIFFICULTY_MUST_BE_POSITIVE_FINITE")
    with localcontext() as ctx:
        ctx.prec = 120
        result = (Decimal(difficulty_one_target) / value).to_integral_value(rounding=ROUND_FLOOR)
    target = int(result)
    if target < 1:
        raise ValueError("DIFFICULTY_EXCEEDS_TARGET_RESOLUTION")
    if target > MAX_TARGET:
        raise ValueError("SHARE_TARGET_OVERFLOW")
    return target
