import unittest

from run_unit import classify_evidence


class Unit001EvidenceClassificationTests(unittest.TestCase):
    def test_missing_evidence_is_blocked(self):
        self.assertEqual(classify_evidence(None), "BLOCKED_NO_RTL_EVIDENCE")

    def test_missing_tool_status_is_blocked(self):
        self.assertEqual(
            classify_evidence({
                "final_status": "BLOCKED",
                "tests": [{"name": "rtl", "status": "BLOCKED"}],
            }),
            "BLOCKED",
        )

    def test_all_real_rtl_tests_pass_only_promotes_to_rtl_pass(self):
        self.assertEqual(
            classify_evidence({
                "final_status": "SHA256D_RTL_PASS",
                "tests": [
                    {"name": "header", "status": "PASS"},
                    {"name": "target", "status": "PASS"},
                ],
            }),
            "RTL_SIMULATION_PASS_ONLY",
        )

    def test_failed_test_does_not_pass(self):
        self.assertEqual(
            classify_evidence({
                "final_status": "FAIL",
                "tests": [{"name": "header", "status": "FAIL"}],
            }),
            "RTL_SIMULATION_FAIL",
        )


if __name__ == "__main__":
    unittest.main()
