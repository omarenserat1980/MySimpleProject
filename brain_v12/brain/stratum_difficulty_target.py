"""Convert a Stratum V1 difficulty into a bounded Bitcoin SHA256d share target.

This pure helper does not infer a target from network difficulty, access a pool,
or submit shares. It uses Bitcoin's difficulty-1 target and decimal arithmetic
so a session driver can explicitly bind the target to the pool's reported share
difficulty without binary-float rounding.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

# Bitcoin difficulty-1 target used by conventional SHA256d Stratum V1 pools.
DIFFICULTY_ONE_TARGET = int(
    "00000000ffff0000000000000000000000000000000000000000000000000000", 16
)
MAX_UINT256 = (1 << 256) - 1


class StratumDifficultyError(ValueError):
    """Invalid difficulty or unrepresentable share target."""


def share_target_from_difficulty(difficulty: Any) -> dict[str, Any]:
    """Return the conventional SHA256d share target for a positive difficulty.

    The target is floor(DIFF1_TARGET / difficulty), bounded to uint256. A target
    of zero is preserved when the requested difficulty exceeds the integer
    target's resolution; it is not silently rounded up to a valid hash.
    """
    if isinstance(difficulty, bool) or difficulty is None:
        raise StratumDifficultyError("INVALID_STRATUM_DIFFICULTY")
    if not isinstance(difficulty, (str, int, float, Decimal)):
        raise StratumDifficultyError("INVALID_STRATUM_DIFFICULTY")
    try:
        value = Decimal(str(difficulty))
    except (InvalidOperation, ValueError) as exc:
        raise StratumDifficultyError("INVALID_STRATUM_DIFFICULTY") from exc
    if not value.is_finite() or value <= 0:
        raise StratumDifficultyError("INVALID_STRATUM_DIFFICULTY")
    target = int(Decimal(DIFFICULTY_ONE_TARGET) / value)
    if not 0 <= target <= MAX_UINT256:
        raise StratumDifficultyError("SHARE_TARGET_OUT_OF_RANGE")
    return {
        "evidence_class": "DERIVED_SHARE_TARGET_FROM_POOL_REPORTED_DIFFICULTY",
        "difficulty": str(value),
        "share_target": target,
        "share_target_hex": f"{target:064x}",
        "difficulty_one_target": DIFFICULTY_ONE_TARGET,
        "pool_reported_difficulty_used": True,
        "network_target_inferred": False,
        "live_pool_evidence": False,
        "share_acceptance_verified": False,
        "revenue_verified": False,
    }
