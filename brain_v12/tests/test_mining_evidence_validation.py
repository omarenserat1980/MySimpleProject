import unittest

from brain_v12.brain.brain_owned_mining_contract import (
    EXECUTION_TARGET,
    classify_evidence,
)


def valid_evidence(**overrides):
    evidence = {
        "source": "pool_api",
        "worker_id": "brain-worker-test",
        "pool_source_verified": True,
        "brain_runtime_attested": True,
        "compute_host": EXECUTION_TARGET,
        "physical_device_computation": False,
        "external_miner_execution": False,
        "hashrate_hs": 12.5,
        "accepted_shares": 3,
    }
    evidence.update(overrides)
    return evidence


class MiningEvidenceValidationTests(unittest.TestCase):
    def test_valid_pool_activity_does_not_claim_revenue(self):
        result = classify_evidence(valid_evidence())
        self.assertEqual(result["status"], "BRAIN_RUNTIME_POOL_ACTIVITY_VERIFIED")
        self.assertTrue(result["counts_as_real_mining"])
        self.assertFalse(result["revenue_verified"])

    def test_rejects_nan_and_infinite_hashrate(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(hashrate=value):
                result = classify_evidence(valid_evidence(hashrate_hs=value))
                self.assertEqual(result["status"], "INVALID_EVIDENCE_FIELDS")
                self.assertFalse(result["counts_as_real_mining"])

    def test_rejects_boolean_telemetry(self):
        for key in ("hashrate_hs", "accepted_shares"):
            with self.subTest(field=key):
                result = classify_evidence(valid_evidence(**{key: True}))
                self.assertEqual(result["status"], "INVALID_EVIDENCE_FIELDS")
                self.assertFalse(result["counts_as_real_mining"])

    def test_rejects_fractional_or_non_finite_accepted_share_count(self):
        for value in (1.5, float("nan"), float("inf"), -1):
            with self.subTest(accepted_shares=value):
                result = classify_evidence(valid_evidence(accepted_shares=value))
                self.assertEqual(result["status"], "INVALID_EVIDENCE_FIELDS")
                self.assertFalse(result["counts_as_real_mining"])

    def test_simulation_never_counts_as_real_mining(self):
        result = classify_evidence(valid_evidence(simulation=True))
        self.assertEqual(result["status"], "SIMULATION_ONLY")
        self.assertFalse(result["counts_as_real_mining"])
        self.assertFalse(result["revenue_verified"])


if __name__ == "__main__":
    unittest.main()
