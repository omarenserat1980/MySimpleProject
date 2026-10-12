import unittest

from brain_v12.tools.merge_request_executor import evaluate


def good_pr():
    return {
        "state": "OPEN",
        "isDraft": False,
        "mergeable": "MERGEABLE",
        "reviewDecision": "APPROVED",
        "statusCheckRollup": [
            {"name": "unit-tests", "conclusion": "SUCCESS"},
            {"context": "lint", "state": "success"},
        ],
    }


class MergeGateTests(unittest.TestCase):
    def test_ready_when_all_gates_pass(self):
        self.assertEqual(evaluate(good_pr()), [])

    def test_blocks_draft_and_missing_approval(self):
        pr = good_pr()
        pr["isDraft"] = True
        pr["reviewDecision"] = "REVIEW_REQUIRED"
        blockers = evaluate(pr)
        self.assertIn("PR_IS_DRAFT", blockers)
        self.assertIn("REVIEW_NOT_APPROVED", blockers)

    def test_blocks_failed_or_pending_check(self):
        pr = good_pr()
        pr["statusCheckRollup"].append({"name": "integration", "state": "IN_PROGRESS"})
        self.assertIn("CHECK_NOT_SUCCESS:integration:IN_PROGRESS", evaluate(pr))

    def test_blocks_missing_check_evidence(self):
        pr = good_pr()
        pr["statusCheckRollup"] = []
        self.assertIn("NO_CHECK_EVIDENCE", evaluate(pr))


if __name__ == "__main__":
    unittest.main()
