import unittest

from brain_v12.brain.bitcoin_compact_target import compact_bits_to_target
from brain_v12.brain.mining_share_candidate import validate_share_candidate
from brain_v12.brain.stratum_job_header import build_normalized_header


class MiningShareCandidateIntegrationTests(unittest.TestCase):
    def setUp(self):
        # Canonical Bitcoin mainnet genesis header; no pool/network assumptions.
        self.nonce = 0x7C2BAC1D
        self.header = build_normalized_header(
            version_le=bytes.fromhex("01000000"),
            prevhash_header_bytes=bytes(32),
            merkle_root_header_bytes=bytes.fromhex(
                "3ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa4b1e5e4a"
            ),
            ntime_le=bytes.fromhex("29ab5f49"),
            nbits_le=bytes.fromhex("ffff001d"),
            nonce=self.nonce,
        )
        self.target = compact_bits_to_target(0x1D00FFFF)

    def test_genesis_header_is_a_valid_local_candidate_for_matching_job(self):
        result = validate_share_candidate(
            header=self.header,
            target=self.target,
            nonce=self.nonce,
            job_id="genesis-vector",
            expected_job_id="genesis-vector",
        )
        self.assertTrue(result["meets_target"])
        self.assertEqual(result["status"], "VALID_LOCAL_CANDIDATE_UNSUBMITTED")
        self.assertEqual(
            result["hash_hex"],
            "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f",
        )
        self.assertFalse(result["pool_submission_attempted"])
        self.assertFalse(result["pool_acceptance_verified"])
        self.assertFalse(result["counts_as_real_pool_mining"])
        self.assertEqual(result["evidence_class"], "LOCAL_PROOF_OF_WORK_CANDIDATE_ONLY")

    def test_rejects_job_mismatch(self):
        with self.assertRaisesRegex(ValueError, "SHARE_JOB_ID_MISMATCH"):
            validate_share_candidate(
                header=self.header,
                target=self.target,
                nonce=self.nonce,
                job_id="stale-job",
                expected_job_id="current-job",
            )

    def test_rejects_nonce_not_matching_header(self):
        with self.assertRaisesRegex(ValueError, "HEADER_NONCE_MISMATCH"):
            validate_share_candidate(
                header=self.header,
                target=self.target,
                nonce=self.nonce - 1,
                job_id="genesis-vector",
                expected_job_id="genesis-vector",
            )


if __name__ == "__main__":
    unittest.main()
