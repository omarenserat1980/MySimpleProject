import unittest

from brain_v12.asic.bitcoin_pow_simulator import (
    MAX_ATTEMPTS,
    simulate_pow,
    sha256d,
)


class BitcoinPowSimulatorTests(unittest.TestCase):
    def test_sha256d_known_empty_input_vector(self):
        self.assertEqual(
            sha256d(b"").hex(),
            "5df6e0e2761359d30a8275058e299fcc0381534545f55cf43e41983f5d4c9456",
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
