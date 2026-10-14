"""Tests for the independent Bitcoin proof-of-work reference oracle."""
import unittest

from brain_v12.brain.bitcoin_pow_reference import (
    check_proof_of_work,
    compact_bits_to_target,
    serialize_block_header,
    sha256d,
)


class BitcoinPowReferenceTests(unittest.TestCase):
    def test_sha256d_known_empty_vector(self):
        self.assertEqual(
            sha256d(b"").hex(),
            "5df6e0e2761359d30a8275058e299fcc0381534545f55cf43e41983f5d4c9456",
        )

    def test_header_is_exactly_80_bytes_and_hash_fields_reverse(self):
        prev = "11" * 32
        merkle = "22" * 32
        header = serialize_block_header(1, prev, merkle, 1231006505, 0x1D00FFFF, 0)
        self.assertEqual(len(header), 80)
        self.assertEqual(header[4:36], bytes.fromhex(prev)[::-1])
        self.assertEqual(header[36:68], bytes.fromhex(merkle)[::-1])
        self.assertEqual(header[68:72], bytes.fromhex("29ab5f49"))
        self.assertEqual(header[72:76], bytes.fromhex("ffff001d"))
        self.assertEqual(header[76:80], b"\x00\x00\x00\x00")

    def test_compact_target_for_genesis_bits(self):
        self.assertEqual(
            compact_bits_to_target(0x1D00FFFF),
            0xFFFF << (8 * (0x1D - 3)),
        )

    def test_invalid_compact_targets_fail_closed(self):
        for bits in (0, 0x1D80FFFF, 0x2300FFFF, -1, 1 << 32):
            with self.subTest(bits=bits):
                with self.assertRaises(ValueError):
                    compact_bits_to_target(bits)

    def test_work_check_reports_no_external_claims(self):
        header = serialize_block_header(1, "00" * 32, "00" * 32, 1, 0x207FFFFF, 0)
        result = check_proof_of_work(header, 0x207FFFFF)
        self.assertIn("valid", result)
        self.assertFalse(result["live_mining"])
        self.assertFalse(result["pool_acceptance"])
        self.assertFalse(result["revenue_verified"])
        self.assertEqual(result["evidence_level"], "LOCAL_REFERENCE_CHECK_ONLY")

    def test_bad_header_length_rejected(self):
        with self.assertRaisesRegex(ValueError, "INVALID_HEADER_LENGTH"):
            check_proof_of_work(b"short", 0x207FFFFF)


if __name__ == "__main__":
    unittest.main()
