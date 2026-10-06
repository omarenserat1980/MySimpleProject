import unittest
from brain_v12.business.cl_000003_master_release_gate import decide, REQUIRED

class MasterReleaseGateTests(unittest.TestCase):
    def good(self):
        return {
            "film_id": "CL3-FILM-001",
            "film_version": "v1",
            "production_run": "RUN-001",
            **{k: {"passed": True, "evidence_ref": f"evidence/{k}", "evidence_sha256": "a" * 64} for k in REQUIRED},
        }

    def test_missing_any_gate_blocks_publish(self):
        result = decide({})
        self.assertFalse(result["publish_authorized"])
        self.assertEqual(result["status"], "DO_NOT_PUBLISH")
        self.assertIn("FILM_ID_REQUIRED", result["failures"])

    def test_technical_pass_does_not_bypass_cinematic(self):
        evidence = self.good()
        evidence["cinematic"] = {"passed": False}
        result = decide(evidence)
        self.assertFalse(result["publish_authorized"])
        self.assertIn("CINEMATIC_PASS_REQUIRED", result["failures"])

    def test_missing_evidence_hash_blocks_publish(self):
        evidence = self.good()
        evidence["rights"].pop("evidence_sha256")
        result = decide(evidence)
        self.assertFalse(result["publish_authorized"])
        self.assertIn("RIGHTS_EVIDENCE_SHA256_REQUIRED", result["failures"])

    def test_all_gates_and_identity_pass_authorizes_release(self):
        result = decide(self.good())
        self.assertTrue(result["publish_authorized"])
        self.assertEqual(result["status"], "MASTER_RELEASE_PASS")
        self.assertEqual(len(result["decision_sha256"]), 64)

if __name__ == "__main__":
    unittest.main()
