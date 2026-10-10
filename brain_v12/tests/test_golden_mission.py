import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from brain_v12.brain.golden_mission import GoldenMissionController


class MemoryEvidenceStore:
    def __init__(self):
        self.items = {}

    def append(self, task_id, kind, payload, producer="test"):
        import hashlib, json
        raw=json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()
        sha=hashlib.sha256(raw).hexdigest()
        item={"evidence_id":"ev-test","task_id":task_id,"kind":kind,"payload":payload,"sha256":sha,"producer":producer}
        self.items[item["evidence_id"]]=item
        return item

    def get(self,evidence_id):
        return self.items.get(evidence_id)

    def verify_hash(self,evidence_id):
        item=self.get(evidence_id)
        return {"ok":bool(item),"sha256":item["sha256"] if item else None}


class GoldenMissionControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.notifications = []
        self.evidence = MemoryEvidenceStore()
        self.controller = GoldenMissionController(
            str(Path(self.tmp.name) / "missions.sqlite3"),
            notifier=lambda mission, message: self.notifications.append((mission["mission_id"], message)) or {"sent": False, "reason": "test"},
            evidence_store=self.evidence,
        )
        self.mission = self.controller.create(
            title="Test mission", objective="Verify a safe test objective",
            acceptance=["objective passes", "evidence hash is verified"],
            estimate_minutes=10, update_minutes=2,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_persists_mission_across_controller_instances(self):
        restored = GoldenMissionController(str(Path(self.tmp.name) / "missions.sqlite3"))
        self.assertEqual(restored.get(self.mission["mission_id"])["status"], "PLANNED")
        self.assertEqual(restored.get(self.mission["mission_id"])["acceptance"], self.mission["acceptance"])

    def test_permission_gate_cannot_be_skipped(self):
        m = self.controller.require_permission(self.mission["mission_id"], "device_admin", "Needs explicit approval")
        self.assertEqual(m["status"], "WAITING_PERMISSION")
        with self.assertRaisesRegex(ValueError, "MISSION_PERMISSION_REQUIRED"):
            self.controller.start(m["mission_id"])
        with self.assertRaisesRegex(ValueError, "PERMISSION_MISMATCH"):
            self.controller.grant_permission(m["mission_id"], "root", "owner")
        m = self.controller.grant_permission(m["mission_id"], "device_admin", "owner")
        self.assertEqual(m["status"], "RUNNING")
        self.assertTrue(m["permission_granted"])
        self.assertTrue(self.notifications)

    def test_cannot_close_without_objective_and_evidence_proof(self):
        self.controller.start(self.mission["mission_id"])
        fake = self.evidence.append(self.mission["mission_id"], "test", {"objective_verified":False,"acceptance_passed":False,"criteria_results":[{"passed":False}]})
        with self.assertRaisesRegex(ValueError, "OBJECTIVE_AND_EVIDENCE_VERIFICATION_REQUIRED"):
            self.controller.close(self.mission["mission_id"], fake["evidence_id"], fake["sha256"])
        self.assertEqual(self.controller.get(self.mission["mission_id"])["status"], "RUNNING")

    def test_cannot_close_using_another_missions_evidence(self):
        self.controller.start(self.mission["mission_id"])
        fake = self.evidence.append("other-mission", "test", {"objective_verified":True,"acceptance_passed":True,"criteria_results":[{"passed":True}]})
        with self.assertRaisesRegex(ValueError, "MISSION_EVIDENCE_NOT_FOUND_OR_MISMATCHED"):
            self.controller.close(self.mission["mission_id"], fake["evidence_id"], fake["sha256"])

    def test_closes_only_with_verified_objective_evidence(self):
        self.controller.start(self.mission["mission_id"])
        proof = self.evidence.append(self.mission["mission_id"], "objective-verification", {
            "objective_verified":True,"acceptance_passed":True,
            "criteria_results":[{"criterion":"objective passes","passed":True},{"criterion":"evidence hash is verified","passed":True}],
        },"brain-golden-mission-verifier")
        m = self.controller.close(self.mission["mission_id"], proof["evidence_id"], proof["sha256"], "all acceptance criteria passed")
        self.assertEqual(m["status"], "CLOSED")
        self.assertEqual(m["result"]["evidence_sha256"], proof["sha256"])
        self.assertTrue(any(e["event"] == "GOLDEN_LOOP_CLOSED" for e in m["evidence"]))

    def test_checkpoint_updates_estimate(self):
        self.controller.start(self.mission["mission_id"])
        m=self.controller.checkpoint(self.mission["mission_id"],"first step",25,next_estimate_minutes=20)
        self.assertEqual(m["status"],"RUNNING")
        self.assertEqual(m["attempts"],0)
        self.assertEqual(m["estimate_minutes"],20)

    def test_email_is_explicitly_unconfigured_when_missing(self):
        with patch.dict("os.environ", {}, clear=True):
            result=GoldenMissionController._send_email(self.mission,"test")
        self.assertEqual(result["reason"],"EMAIL_NOT_CONFIGURED")

    def test_retry_limit_blocks_and_notifies(self):
        m=self.controller.create("Bounded","Retry bounded test",["passes"],estimate_minutes=3,max_attempts=2)
        self.controller.start(m["mission_id"])
        first=self.controller.record_retry(m["mission_id"],"first failure")
        self.assertEqual(first["status"],"RUNNING")
        self.assertEqual(first["attempts"],1)
        second=self.controller.record_retry(m["mission_id"],"second failure")
        self.assertEqual(second["status"],"BLOCKED")
        self.assertEqual(second["attempts"],2)
        self.assertTrue(any(e["event"]=="RETRY_LIMIT_REACHED" for e in second["evidence"]))

if __name__ == "__main__":
    unittest.main()
