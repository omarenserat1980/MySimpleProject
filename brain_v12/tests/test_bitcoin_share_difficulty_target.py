import math
import unittest
from brain_v12.brain.bitcoin_share_difficulty_target import difficulty_to_target


class BitcoinShareDifficultyTargetTests(unittest.TestCase):
    def setUp(self):
        self.base = 0xFFFF << (8 * (0x1D - 3))

    def test_difficulty_one_and_two(self):
        self.assertEqual(difficulty_to_target(1, difficulty_one_target=self.base), self.base)
        self.assertEqual(difficulty_to_target(2, difficulty_one_target=self.base), self.base // 2)

    def test_decimal_string_and_fractional_difficulty(self):
        self.assertEqual(difficulty_to_target('0.5', difficulty_one_target=self.base), self.base * 2)
        self.assertEqual(difficulty_to_target('2.5', difficulty_one_target=1000), 400)

    def test_rejects_invalid_difficulty_and_baseline(self):
        for difficulty in (True, 0, -1, float('nan'), float('inf'), 'nope', '0'):
            with self.subTest(difficulty=difficulty), self.assertRaises(ValueError):
                difficulty_to_target(difficulty, difficulty_one_target=self.base)
        for base in (True, 0, -1, 1 << 256, 1.5):
            with self.subTest(base=base), self.assertRaises(ValueError):
                difficulty_to_target(1, difficulty_one_target=base)

    def test_rejects_targets_below_integer_resolution(self):
        with self.assertRaises(ValueError):
            difficulty_to_target(100, difficulty_one_target=1)

if __name__ == '__main__':
    unittest.main()
