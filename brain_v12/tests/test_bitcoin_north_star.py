import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.bitcoin_north_star import BitcoinNorthStar, MISSION
from brain_v12.brain.run_evidence_store import RunEvidenceStore


class BitcoinNorthStarTests(unittest.TestCase):
    def _compass(self, temp):
        store = RunEvidenceStore(Path(temp) / "north-star.jsonl")
        return BitcoinNorthStar(evidence_store=store), store

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
        result = BitcoinNorthStar().assess({
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

    def test_assessment_event_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            compass, store = self._compass(temp)
            task = {
                "task_id": "economic-gate",
                "tags": ["MINING_ECONOMICS"],
                "expected_progress": 0.8,
            }
            compass.assess(task)
            compass.assess(task)
            events = store.read_all()
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["event_type"], "BITCOIN_NORTH_STAR_ASSESSMENT")

    def test_repeated_blocker_reuses_stable_identity_and_does_not_open_a_new_cycle(self):
        with tempfile.TemporaryDirectory() as temp:
            compass, store = self._compass(temp)
            task = {
                "task_id": "stratum-gate",
                "component": "stratum",
                "blocker_key": "POOL_SHARE_PROOF_MISSING",
                "blocker": "No independently verified accepted share",
                "blocker_next_action": "Obtain pool-side accepted-share evidence",
                "tags": ["ACCEPTED_SHARE_PROOF"],
            }
            compass.assess(task)
            first = compass.blocker_snapshot(task)
            count_after_first = len(store.read_all())
            compass.assess(task)
            second = compass.blocker_snapshot(task)
            self.assertEqual(first["blocker_id"], second["blocker_id"])
            self.assertEqual(first["state"], "ACTION_REQUIRED")
            self.assertEqual(second["state"], "ACTION_REQUIRED")
            self.assertEqual(len(store.read_all()), count_after_first)
            compass.assess({**task, "task_id": "another-run-same-blocker"})
            events = store.read_all()
            blocker_events = [event for event in events
                              if event["event_type"] == "BITCOIN_NORTH_STAR_BLOCKER"]
            self.assertEqual(len(blocker_events), 1)
            self.assertEqual(compass.blocker_snapshot(task)["blocker_id"], first["blocker_id"])

    def test_blocker_requires_ordered_transitions_and_verified_closure_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            compass, _ = self._compass(temp)
            task = {
                "task_id": "stratum-gate",
                "component": "stratum",
                "blocker_key": "POOL_SHARE_PROOF_MISSING",
                "blocker": "Accepted share not independently proven",
                "next_action": "Collect pool-side evidence",
            }
            compass.record_blocker(task, state="ACTION_REQUIRED")
            with self.assertRaisesRegex(ValueError, "INVALID_BLOCKER_TRANSITION"):
                compass.record_blocker(task, state="CLOSED", evidence_status="VERIFIED",
                                        evidence_ref="pool-dashboard:share-1",
                                        evidence_source="authenticated-pool-dashboard")
            with self.assertRaisesRegex(ValueError, "CLOSURE_REQUIRES_VERIFIED"):
                compass.record_blocker(task, state="VERIFYING")
                compass.record_blocker(task, state="CLOSED", evidence_ref="share-1",
                                        evidence_source="pool-dashboard", evidence_status="MISSING")
            closed = compass.record_blocker(
                task, state="CLOSED", evidence_ref="pool-dashboard:share-1",
                evidence_source="authenticated-pool-dashboard", evidence_status="VERIFIED",
            )
            self.assertEqual(closed["state"], "CLOSED")
            self.assertEqual(compass.blocker_snapshot(task)["state"], "CLOSED")
            count_after_close = len(compass.evidence_store.read_all())
            compass.assess({**task, "tags": ["ACCEPTED_SHARE_PROOF"]})
            self.assertEqual(compass.blocker_snapshot(task)["state"], "CLOSED")
            self.assertEqual(len(compass.evidence_store.read_all()), count_after_close)

    def test_closure_requires_reference_and_source(self):
        with tempfile.TemporaryDirectory() as temp:
            compass, _ = self._compass(temp)
            task = {"task_id": "payout", "component": "revenue", "blocker_key": "PAYOUT_UNVERIFIED"}
            compass.record_blocker(task, state="ACTION_REQUIRED")
            compass.record_blocker(task, state="VERIFYING")
            with self.assertRaisesRegex(ValueError, "CLOSURE_REQUIRES_EVIDENCE_REFERENCE_AND_SOURCE"):
                compass.record_blocker(task, state="CLOSED", evidence_status="VERIFIED",
                                       evidence_ref="txid-only")

    def test_no_store_cannot_claim_persistent_blocker_state(self):
        with self.assertRaisesRegex(RuntimeError, "EVIDENCE_STORE_REQUIRED"):
            BitcoinNorthStar().record_blocker(
                {"task_id": "stratum", "component": "stratum", "blocker_key": "POOL_PROOF"},
                state="ACTION_REQUIRED",
            )


if __name__ == "__main__":
    unittest.main()
