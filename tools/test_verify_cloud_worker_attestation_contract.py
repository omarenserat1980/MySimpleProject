import unittest

from tools.verify_cloud_worker_attestation_contract import assess


class AttestationContractTests(unittest.TestCase):
    def test_missing_api_heartbeat_fails_closed(self):
        result = assess({
            "ok": True, "status": "healthy", "state": "NOT_RUNNING",
            "worker": {"state": "NOT_RUNNING", "verified": False, "reason": "HEARTBEAT_MISSING"},
        })
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("API_DOES_NOT_ATTEST_A_VERIFIED_LIVE_WORKER", result["findings"])

    def test_worker_health_alone_does_not_attest_api_worker(self):
        api = {"ok": True, "status": "healthy", "state": "NOT_RUNNING",
               "worker": {"state": "NOT_RUNNING", "verified": False}}
        worker = {"ok": True, "service": "brain-cloud-worker",
                  "workers": [{"workerId": "supervisor", "status": "running"}]}
        result = assess(api, worker)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(result["worker_endpoint_healthy"])
        self.assertIn("WORKER_ENDPOINT_AND_API_ATTESTATION_NOT_YET_BRIDGED", result["findings"])

    def test_verified_api_attestation_passes(self):
        result = assess({"ok": True, "status": "healthy", "state": "RUNNING",
                         "worker": {"state": "RUNNING", "verified": True}})
        self.assertEqual(result["status"], "VERIFIED")

    def test_wrong_worker_shape_fails_closed(self):
        result = assess({"state": "NOT_RUNNING", "worker": {"verified": False}},
                        {"ok": True, "service": "unexpected", "workers": []})
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["worker_endpoint_healthy"])


if __name__ == "__main__":
    unittest.main()
