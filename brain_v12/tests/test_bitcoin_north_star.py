import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.bitcoin_north_star import BitcoinNorthStar, MISSION
from brain_v12.brain.run_evidence_store import RunEvidenceStore


class BitcoinNorthStarTests(unittest.TestCase):
    def test_direct_bitcoin_work_advances(self):
        result = BitcoinNorthStar().assess({
            "task_id": "stratum-contract",
            "tags": ["STRATUM_CONNECTIVITY"],
            "expected_progress": 0.9,
            "evidence_status": "VERIFIED",
        })
        self.assertEqual(result.mission, MISSION)
        self.assertEqual(result.status, "ON_MISSION")
        self.assertFalse(result.revenue_claim_allowed)

    def test_unrelated_task_is_deprioritized(self):
        result = BitcoinNorthStar().assess({
            "task_id": "unrelated-ui-polish",
            "tags": ["UI_POLISH"],
            "expected_progress": 1.0,
            "evidence_status": "VERIFIED",
        })
        self.assertEqual(result.status, "OFF_COURSE")
        self.assertEqual(result.direction, "DEPRIORITIZE")

    def test_high_risk_and_live_mining_require_approval(self):
        compass = BitcoinNorthStar()
        result = compass.assess({
            "task_id": "enable-pool-mining",
            "tags": ["REAL_BTC_MINING", "LIVE_MINING"],
            "risk": "CRITICAL",
            "expected_progress": 1.0,
        })
        self.assertEqual(result.status, "BLOCKED")
        self.assertTrue(result.requires_approval)
        self.assertFalse(result.revenue_claim_allowed)

    def test_explicit_dependency_stays_supporting_until_proven_progress(self):
        result = BitcoinNorthStar().assess({
            "task_id": "executor-readiness",
            "tags": ["EXECUTOR_READINESS"],
            "expected_progress": 0.1,
            "evidence_status": "MISSING",
        })
        self.assertEqual(result.status, "SUPPORTING")

    def test_missing_task_id_rejected(self):
        with self.assertRaisesRegex(ValueError, "TASK_ID_REQUIRED"):
            BitcoinNorthStar().assess({"tags": ["REAL_BTC_MINING"]})

    def test_assessments_are_written_to_existing_evidence_store(self):
        with tempfile.TemporaryDirectory() as temp:
            store = RunEvidenceStore(Path(temp) / "north-star.jsonl")
            compass = BitcoinNorthStar(evidence_store=store)
            first = compass.assess({
                "task_id": "economic-gate",
                "tags": ["MINING_ECONOMICS"],
                "expected_progress": 0.8,
            })
            events = store.read_all()
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["event_type"], "BITCOIN_NORTH_STAR_ASSESSMENT")
            self.assertEqual(events[0]["payload"]["task_id"], first.task_id)

    def test_single_letter_n_is_bitcoin_north_star_command(self):
        from brain_v12.brain.decision_engine import DecisionEngine
        engine = DecisionEngine(north_star=BitcoinNorthStar())
        self.assertIn("Bitcoin mining mission", engine.normalize_goal("N"))
        self.assertEqual(engine.normalize_goal(" n "), engine.normalize_goal("north star"))
        options = engine.generate("N")
        result = engine.choose("N", options)
        self.assertEqual(result["status"], "DECIDED")
        self.assertEqual(result["goal"], "N")
        self.assertIn("Bitcoin mining mission", result["normalized_goal"])
        self.assertEqual(result["north_star"]["mission"], MISSION)


if __name__ == "__main__":
    unittest.main()
