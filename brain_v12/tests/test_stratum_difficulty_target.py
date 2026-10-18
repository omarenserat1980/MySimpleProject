"""Unit tests for Stratum difficulty-to-target conversion."""
import unittest
from decimal import Decimal

from brain_v12.brain.stratum_difficulty_target import (
    DIFFICULTY_ONE_TARGET,
    MAX_UINT256,
    StratumDifficultyError,
    share_target_from_difficulty,
)


class StratumDifficultyTargetTests(unittest.TestCase):
    def test_difficulty_one_returns_reference_target(self):
        result = share_target_from_difficulty(1)
        self.assertEqual(result["share_target"], DIFFICULTY_ONE_TARGET)
        self.assertEqual(result["share_target_hex"], f"{DIFFICULTY_ONE_TARGET:064x}")
        self.assertTrue(result["pool_reported_difficulty_used"])
        self.assertFalse(result["share_acceptance_verified"])
        self.assertFalse(result["revenue_verified"])

    def test_difficulty_two_halves_target_with_decimal_arithmetic(self):
        result = share_target_from_difficulty(Decimal("2"))
        self.assertEqual(result["share_target"], DIFFICULTY_ONE_TARGET // 2)

    def test_fractional_difficulty_increases_target(self):
        result = share_target_from_difficulty("0.5")
        self.assertEqual(result["share_target"], DIFFICULTY_ONE_TARGET * 2)
        self.assertLessEqual(result["share_target"], MAX_UINT256)

    def test_invalid_difficulties_fail_closed(self):
        for value in (None, True, False, 0, -1, 0.0, float("nan"),
                      float("inf"), "-Infinity", "not-a-number", ""):
            with self.subTest(value=value):
                with self.assertRaises(StratumDifficultyError):
                    share_target_from_difficulty(value)

    def test_extreme_finite_difficulty_does_not_round_target_up(self):
        result = share_target_from_difficulty("1e1000")
        self.assertEqual(result["share_target"], 0)
        self.assertEqual(result["share_target_hex"], "0" * 64)


if __name__ == "__main__":
    unittest.main()
