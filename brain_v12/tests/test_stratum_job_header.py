import unittest

from brain_v12.brain.stratum_job_header import build_normalized_header


class NormalizedBitcoinHeaderTests(unittest.TestCase):
    def fields(self):
        return {
            "version_le": bytes.fromhex("01000020"),
            "prevhash_header_bytes": bytes(range(32)),
            "merkle_root_header_bytes": bytes(range(32, 64)),
            "ntime_le": bytes.fromhex("78563412"),
            "nbits_le": bytes.fromhex("ffff001d"),
            "nonce": 0x12345678,
        }

    def test_builds_exactly_80_bytes_and_preserves_normalized_field_order(self):
        header = build_normalized_header(**self.fields())
        self.assertEqual(len(header), 80)
        self.assertEqual(header[0:4], bytes.fromhex("01000020"))
        self.assertEqual(header[4:36], bytes(range(32)))
        self.assertEqual(header[36:68], bytes(range(32, 64)))
        self.assertEqual(header[68:72], bytes.fromhex("78563412"))
        self.assertEqual(header[72:76], bytes.fromhex("ffff001d"))
        self.assertEqual(header[76:80], bytes.fromhex("78563412"))

    def test_rejects_wrong_field_widths(self):
        for field, value in (
            ("version_le", b"123"),
            ("prevhash_header_bytes", b"x" * 31),
            ("merkle_root_header_bytes", b"x" * 33),
            ("ntime_le", b"12345"),
            ("nbits_le", b""),
        ):
            fields = self.fields()
            fields[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                build_normalized_header(**fields)

    def test_rejects_invalid_nonce_types_and_ranges(self):
        for nonce in (True, -1, 2**32, 1.5, "1"):
            fields = self.fields()
            fields["nonce"] = nonce
            with self.subTest(nonce=nonce), self.assertRaises(ValueError):
                build_normalized_header(**fields)


if __name__ == "__main__":
    unittest.main()
