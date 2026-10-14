import unittest

from brain_v12.asic.bitcoin_pow_simulator import (
    MAX_ATTEMPTS,
    decode_compact_target,
    simulate_pow,
    sha256d,
)


class BitcoinPowSimulatorTests(unittest.TestCase):
    def test_sha256d_known_empty_input_vector(self):
        self.assertEqual(
            sha256d(b"").hex(),
            "5df6e0e2761359d30a8275058e299fcc0381534545f55cf43e41983f5d4c9456",
        )



    def test_genesis_compact_target_decoding(self):
        self.assertEqual(
            decode_compact_target(0x1D00FFFF),
            0xFFFF << (8 * (0x1D - 3)),
        )

    def test_compact_target_rejects_invalid_encodings(self):
        for bits, reason in [
            (-1, "COMPACT_BITS_MUST_BE_UINT32"),
            (1 << 32, "COMPACT_BITS_MUST_BE_UINT32"),
            (0x1D80FFFF, "NEGATIVE_COMPACT_TARGET"),
            (0x1D000000, "ZERO_COMPACT_TARGET"),
            (0x23000001, "COMPACT_TARGET_OVERFLOW"),
        ]:
            with self.subTest(bits=bits):
                with self.assertRaisesRegex(ValueError, reason):
                    decode_compact_target(bits)

    def test_bitcoin_genesis_header_pow_vector(self):
        # Canonical Bitcoin genesis block header (wire serialization).
        header = bytes.fromhex(
            "01000000"
            + "00" * 32
            + "3ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa4b1e5e4a"
            + "29ab5f49"
            + "ffff001d"
            + "1dac2b7c"
        )
        target = 0xFFFF << (8 * (0x1D - 3))
        result = simulate_pow(
            header, target, start_nonce=2083236893, max_attempts=1
        )
        self.assertTrue(result.found)
        self.assertEqual(result.nonce, 2083236893)
        self.assertEqual(
            result.hash_hex,
            "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f",
        )

    def test_easy_target_finds_nonce_and_marks_simulation_only(self):
        result = simulate_pow(bytes(80), (1 << 256) - 1, start_nonce=7, max_attempts=1)
        self.assertTrue(result.found)
        self.assertEqual(result.nonce, 7)
        self.assertEqual(result.attempts, 1)
        self.assertLessEqual(result.hash_value, result.target)
        self.assertEqual(result.hash_hex, result.hash_value.to_bytes(32, "little")[::-1].hex())
        self.assertFalse(result.live_mining)
        self.assertFalse(result.pool_connected)
        self.assertFalse(result.revenue_verified)
        self.assertEqual(result.as_dict()["evidence_scope"], "BOUNDED_OFFLINE_SOFTWARE_SIMULATION")

    def test_impossible_zero_target_stops_at_attempt_bound(self):
        result = simulate_pow(bytes(80), 0, max_attempts=3)
        self.assertFalse(result.found)
        self.assertEqual(result.attempts, 3)
        self.assertEqual(result.status, "SIMULATION_LIMIT_REACHED")
        self.assertIsNone(result.nonce)

    def test_rejects_invalid_header_and_bounds(self):
        with self.assertRaisesRegex(ValueError, "HEADER_MUST_BE_EXACTLY_80_BYTES"):
            simulate_pow(b"short", 1)
        with self.assertRaisesRegex(ValueError, "TARGET_MUST_BE_A_256_BIT_UNSIGNED_INTEGER"):
            simulate_pow(bytes(80), -1)
        with self.assertRaisesRegex(ValueError, "MAX_ATTEMPTS_MUST_BE_BETWEEN"):
            simulate_pow(bytes(80), 1, max_attempts=MAX_ATTEMPTS + 1)
        with self.assertRaisesRegex(ValueError, "START_NONCE_OUT_OF_RANGE"):
            simulate_pow(bytes(80), 1, start_nonce=1 << 32)


if __name__ == "__main__":
    unittest.main()
