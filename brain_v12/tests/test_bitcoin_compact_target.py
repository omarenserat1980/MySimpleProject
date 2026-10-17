import unittest
from brain_v12.brain.bitcoin_compact_target import compact_bits_to_target, target_to_compact_bits


class BitcoinCompactTargetTests(unittest.TestCase):
    def test_mainnet_genesis_nbits_decodes_to_known_target(self):
        expected = 0xFFFF << (8 * (0x1D - 3))
        self.assertEqual(compact_bits_to_target(0x1D00FFFF), expected)
        self.assertEqual(target_to_compact_bits(expected), 0x1D00FFFF)

    def test_round_trip_representable_targets(self):
        for compact in (0x1B0404CB, 0x1D00FFFF, 0x207FFFFF):
            target = compact_bits_to_target(compact)
            self.assertEqual(target_to_compact_bits(target), compact)

    def test_rejects_invalid_or_malformed_values(self):
        for compact in (True, -1, 1 << 32, 0, 0x1D80FFFF, 0x23000001, 0x01000001):
            with self.subTest(compact=compact), self.assertRaises(ValueError):
                compact_bits_to_target(compact)
        for target in (True, 0, -1, 1 << 256, 1.5):
            with self.subTest(target=target), self.assertRaises(ValueError):
                target_to_compact_bits(target)

if __name__ == '__main__':
    unittest.main()
