import unittest

from brain_v12.brain.brain_owned_compute_runtime import double_sha256
from brain_v12.brain.mining_share_candidate import validate_share_candidate


class MiningShareCandidateTests(unittest.TestCase):
    def make_header(self, nonce=0):
        return bytes(76) + nonce.to_bytes(4, "little")

    def test_valid_candidate_is_bound_to_job_header_nonce_and_target(self):
        header = self.make_header(7)
        result = validate_share_candidate(
            header=header,
            target=(1 << 256) - 1,
            nonce=7,
            job_id="job-A",
            expected_job_id="job-A",
        )
        self.assertEqual(result["status"], "VALID_LOCAL_CANDIDATE_UNSUBMITTED")
        self.assertEqual(result["hash_hex"], double_sha256(header)[::-1].hex())
        self.assertTrue(result["meets_target"])
        self.assertFalse(result["pool_submission_attempted"])
        self.assertFalse(result["pool_acceptance_verified"])
        self.assertFalse(result["counts_as_real_pool_mining"])

    def test_rejects_job_mismatch(self):
        with self.assertRaisesRegex(ValueError, "SHARE_JOB_ID_MISMATCH"):
            validate_share_candidate(
                header=self.make_header(),
                target=(1 << 256) - 1,
                nonce=0,
                job_id="old-job",
                expected_job_id="new-job",
            )

    def test_rejects_nonce_not_encoded_in_header(self):
        with self.assertRaisesRegex(ValueError, "HEADER_NONCE_MISMATCH"):
            validate_share_candidate(
                header=self.make_header(9),
                target=(1 << 256) - 1,
                nonce=8,
                job_id="job-A",
                expected_job_id="job-A",
            )

    def test_reports_target_failure_without_claiming_submission(self):
        result = validate_share_candidate(
            header=self.make_header(0),
            target=1,
            nonce=0,
            job_id="job-A",
            expected_job_id="job-A",
        )
        self.assertEqual(result["status"], "INVALID_LOCAL_CANDIDATE")
        self.assertFalse(result["meets_target"])
        self.assertFalse(result["pool_acceptance_verified"])

    def test_rejects_invalid_header_target_and_nonce_types(self):
        with self.assertRaises(ValueError):
            validate_share_candidate(
                header=b"short", target=(1 << 256) - 1, nonce=0,
                job_id="job-A", expected_job_id="job-A",
            )
        with self.assertRaises(ValueError):
            validate_share_candidate(
                header=self.make_header(), target=0, nonce=0,
                job_id="job-A", expected_job_id="job-A",
            )
        with self.assertRaises(ValueError):
            validate_share_candidate(
                header=self.make_header(), target=(1 << 256) - 1, nonce=True,
                job_id="job-A", expected_job_id="job-A",
            )


if __name__ == "__main__":
    unittest.main()
