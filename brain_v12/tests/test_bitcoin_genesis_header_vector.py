import hashlib
import unittest

from brain_v12.brain.stratum_job_header import build_normalized_header


class BitcoinGenesisHeaderVectorTests(unittest.TestCase):
    def test_genesis_header_serialization_and_sha256d_match_known_vector(self):
        # Bitcoin mainnet genesis block header (block 0), serialized wire order.
        header = build_normalized_header(
            version_le=bytes.fromhex("01000000"),
            prevhash_header_bytes=bytes(32),
            merkle_root_header_bytes=bytes.fromhex(
                "3ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa4b1e5e4a"
            ),
            ntime_le=bytes.fromhex("29ab5f49"),
            nbits_le=bytes.fromhex("ffff001d"),
            nonce=0x7c2bac1d,
        )
        self.assertEqual(len(header), 80)
        self.assertEqual(header[76:80], bytes.fromhex("1dac2b7c"))
        digest = hashlib.sha256(hashlib.sha256(header).digest()).digest()
        self.assertEqual(
            digest[::-1].hex(),
            "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f",
        )


if __name__ == "__main__":
    unittest.main()
