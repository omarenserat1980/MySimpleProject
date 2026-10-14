import unittest

from brain_v12.brain.engineering_factory import EngineeringFactory


class EngineeringFactoryTests(unittest.TestCase):
    def setUp(self):
        self.factory = EngineeringFactory()

    def test_blank_problem_is_blocked(self):
        result = self.factory.propose("  ")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["error"], "PROBLEM_STATEMENT_REQUIRED")

    def test_proposal_connects_problem_to_build_test_integrate_verify(self):
        result = self.factory.propose("Create a reusable Bitcoin Stratum evidence tool")
        self.assertEqual(result["status"], "COMPLETED")
        proposal = result["proposal"]
        self.assertTrue(proposal["mission_aligned"])
        self.assertEqual(
            [step["stage"] for step in proposal["steps"]],
            ["OBSERVE", "DIAGNOSE", "PROPOSE", "BUILD", "TEST", "INTEGRATE", "VERIFY", "LEARN"],
        )
        self.assertIn("contract", [item["kind"] for item in proposal["deliverables"]])
        self.assertFalse(proposal["execution_started"])
        self.assertFalse(proposal["claims"]["real_mining_verified"])
        self.assertFalse(proposal["claims"]["net_profit_verified"])

    def test_unrelated_software_problem_gets_general_acceptance_criteria(self):
        proposal = self.factory.propose("Build a small application to organize notes")["proposal"]
        self.assertFalse(proposal["mission_aligned"])
        self.assertEqual(proposal["work_type"], "SOFTWARE_TOOL_OR_APPLICATION")
        self.assertTrue(any("regression tests" in item.lower() for item in proposal["acceptance_criteria"]))

    def test_evidence_count_does_not_claim_completion(self):
        proposal = self.factory.propose("Improve Bitcoin mining", evidence=[{"test": "passed"}])["proposal"]
        self.assertEqual(proposal["evidence_received"], 1)
        self.assertFalse(proposal["evidence_sufficient_for_completion"])
        self.assertFalse(proposal["claims"]["revenue_verified"])


if __name__ == "__main__":
    unittest.main()
