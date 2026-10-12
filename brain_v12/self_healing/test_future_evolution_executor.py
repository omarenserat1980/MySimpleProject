import unittest
from unittest.mock import patch
from brain_v12.self_healing.future_evolution_executor import execute_prediction

class FutureEvolutionExecutorTests(unittest.TestCase):
    def test_preflight_requires_verification(self):
        r=execute_prediction({"status":"PREDICTED","executor":"python_self_test"})
        self.assertFalse(r["verified"])
        self.assertEqual(r["reason"],"VERIFICATION_REQUIRED")

    def test_unknown_executor_never_claims_success(self):
        r=execute_prediction({"status":"PREDICTED","verification":{},"executor":"unknown"})
        self.assertFalse(r["verified"])
        self.assertNotEqual(r["status"],"VERIFIED_COMPLETED")

    @patch("brain_v12.self_healing.future_evolution_executor.subprocess.run")
    def test_empty_unittest_run_never_claims_success(self, run):
        run.return_value=type("P",(),{"returncode":0,"stdout":"","stderr":""})()
        r=execute_prediction({"status":"PREDICTED","verification":{"required":True},"executor":"python_self_test"})
        self.assertFalse(r["verified"])
        self.assertEqual(r["status"],"FAILED")

    @patch("brain_v12.self_healing.future_evolution_executor.subprocess.run")
    def test_nonzero_test_run_never_claims_success(self, run):
        run.return_value=type("P",(),{"returncode":1,"stdout":"Ran 10 tests in 0.01s\nFAILED (failures=1)\n","stderr":""})()
        r=execute_prediction({"status":"PREDICTED","verification":{"required":True},"executor":"python_self_test"})
        self.assertFalse(r["verified"])
        self.assertEqual(r["status"],"FAILED")

    @patch("brain_v12.self_healing.future_evolution_executor.subprocess.run")
    def test_allowlisted_executor_requires_real_test_evidence(self, run):
        run.return_value=type("P",(),{"returncode":0,"stdout":"Ran 10 tests in 0.01s\nOK\n","stderr":""})()
        r=execute_prediction({"status":"PREDICTED","verification":{"required":True},"executor":"python_self_test"})
        self.assertTrue(r["verified"])
        self.assertEqual(r["status"],"VERIFIED_COMPLETED")
        self.assertEqual(r["evidence"]["returncode"],0)
        self.assertEqual(r["evidence"]["executor"],"python_self_test")
        self.assertTrue(r["evidence"]["tests"])

if __name__=="__main__":
    unittest.main()
