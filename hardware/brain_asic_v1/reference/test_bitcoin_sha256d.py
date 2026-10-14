import unittest
from bitcoin_sha256d import header_hash, meets_target


class BitcoinSha256dTests(unittest.TestCase):
    def test_genesis_block_header_hash(self):
        # Mainnet genesis block header (80 bytes).
        header = bytes.fromhex(
            "01000000"
            + "00" * 32
            + "3ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa4b1e5e4a"
            + "29ab5f49"
            + "ffff001d"
            + "1dac2b7c"
        )
        self.assertEqual(len(header), 80)
        self.assertEqual(
            header_hash(header),
            "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f",
        )

    def test_invalid_header_length_rejected(self):
        with self.assertRaises(ValueError):
            header_hash(b"short")
        with self.assertRaises(ValueError):
            meets_target(b"short", (1 << 256) - 1)

    def test_target_range(self):
        header = bytes(80)
        with self.assertRaises(ValueError):
            meets_target(header, 1 << 256)
        with self.assertRaises(ValueError):
            meets_target(header, -1)


if __name__ == "__main__":
    unittest.main()
