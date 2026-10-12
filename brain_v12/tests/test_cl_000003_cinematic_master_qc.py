import unittest

from brain_v12.business.cl_000003_cinematic_master_qc import CRITERIA, evaluate

class CinematicMasterQCTests(unittest.TestCase):
    def good(self):
        return {k: {"score": 90, "evidence": f"evidence-{k}"} for k in CRITERIA}

    def test_missing_cinematic_evidence_blocks_release(self):
        result = evaluate({})
        self.assertFalse(result["passed"])
        self.assertEqual(result["status"], "DO_NOT_PUBLISH")
        self.assertIn("ALL_CRITERIA_REQUIRED", result["failures"])

    def test_technically_valid_but_cinematically_weak_film_is_rejected(self):
        scores = self.good()
        scores["story"] = {"score": 45, "evidence": "story-review"}
        result = evaluate(scores)
        self.assertFalse(result["passed"])
        self.assertIn("STORY_BELOW_MINIMUM", result["failures"])
        self.assertEqual(result["next_action"], "DIAGNOSE_REWORK_REPLACE")

    def test_all_required_criteria_pass(self):
        result = evaluate(self.good())
        self.assertTrue(result["passed"])
        self.assertEqual(result["status"], "CINEMATIC_PASS")
        self.assertEqual(result["next_action"], "RELEASE_GATE")
