import unittest
from brain_v12.business.cl_000003_publication_guard import require_master_release

class PublicationGuardTests(unittest.TestCase):
    def test_no_evidence_blocks(self):
        r = require_master_release(None)
        self.assertFalse(r["authorized"])

    def test_wrong_master_status_blocks(self):
        r = require_master_release({"status": "CINEMATIC_PASS", "publish_authorized": True})
        self.assertFalse(r["authorized"])
        self.assertEqual(r["status"], "MASTER_RELEASE_PASS_REQUIRED")

    def test_missing_identity_blocks(self):
        r = require_master_release({"status":"MASTER_RELEASE_PASS","publish_authorized":True,"identity":{}})
        self.assertFalse(r["authorized"])
        self.assertEqual(r["status"], "FILM_IDENTITY_REQUIRED")

    def test_valid_master_release_allows_gate(self):
        r = require_master_release({
            "status":"MASTER_RELEASE_PASS",
            "publish_authorized":True,
            "identity":{"film_id":"F1","film_version":"v1","production_run":"R1"},
        })
        self.assertTrue(r["authorized"])

if __name__ == "__main__":
    unittest.main()
