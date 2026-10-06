import unittest
from brain_v12.business.cl_000003_master_release_gate import decide, REQUIRED

class MasterReleaseGateTests(unittest.TestCase):
    def good(self):
        return {k: {"passed": True} for k in REQUIRED}

    def test_missing_any_gate_blocks_publish(self):
        result = decide({})
        self.assertFalse(result["publish_authorized"])
        self.assertEqual(result["status"], "DO_NOT_PUBLISH")

    def test_technical_pass_does_not_bypass_cinematic(self):
        evidence = self.good()
        evidence["cinematic"] = {"passed": False}
        result = decide(evidence)
        self.assertFalse(result["publish_authorized"])
        self.assertIn("CINEMATIC_PASS_REQUIRED", result["failures"])

    def test_all_gates_pass_authorizes_release(self):
        result = decide(self.good())
        self.assertTrue(result["publish_authorized"])
        self.assertEqual(result["status"], "MASTER_RELEASE_PASS")
