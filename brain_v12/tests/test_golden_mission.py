import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from datetime import datetime, timezone

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

    def test_rejects_duplicate_acceptance_criteria(self):
        with self.assertRaisesRegex(ValueError, "ACCEPTANCE_CRITERIA_MUST_BE_UNIQUE"):
            self.controller.create(
                title="Duplicate criteria",
                objective="Reject duplicate acceptance criteria before execution",
                acceptance=["criterion A", "criterion A"],
            )

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
            "objective_verified":True,"acceptance_passed":True,"attempt_number":1,
            "criteria_results":[{"criterion":"objective passes","passed":True},{"criterion":"evidence hash is verified","passed":True}],
        },"brain-golden-mission-verifier")
        m = self.controller.close(self.mission["mission_id"], proof["evidence_id"], proof["sha256"], "all acceptance criteria passed")
        self.assertEqual(m["status"], "CLOSED")
        self.assertEqual(m["result"]["evidence_sha256"], proof["sha256"])
        self.assertTrue(any(e["event"] == "GOLDEN_LOOP_CLOSED" for e in m["evidence"]))

    def test_rejects_evidence_from_previous_attempt(self):
        mission_id = self.mission["mission_id"]
        self.controller.start(mission_id)
        stale = self.evidence.append(mission_id, "objective-verification", {
            "objective_verified": True, "acceptance_passed": True, "attempt_number": 1,
            "criteria_results": [
                {"criterion": "objective passes", "passed": True},
                {"criterion": "evidence hash is verified", "passed": True},
            ],
        }, "test-verifier")
        self.controller.record_retry(mission_id, "first attempt failed")
        with self.assertRaisesRegex(ValueError, "OBJECTIVE_AND_EVIDENCE_VERIFICATION_REQUIRED"):
            self.controller.close(mission_id, stale["evidence_id"], stale["sha256"])
        self.assertEqual(self.controller.get(mission_id)["status"], "RUNNING")

    def test_rejects_evidence_that_does_not_cover_exact_acceptance_criteria(self):
        mission_id = self.mission["mission_id"]
        self.controller.start(mission_id)
        incomplete = self.evidence.append(mission_id, "objective-verification", {
            "objective_verified": True, "acceptance_passed": True, "attempt_number": 1,
            "criteria_results": [
                {"criterion": "some unrelated criterion", "passed": True},
                {"criterion": "objective passes", "passed": True},
            ],
        }, "test-verifier")
        with self.assertRaisesRegex(ValueError, "OBJECTIVE_AND_EVIDENCE_VERIFICATION_REQUIRED"):
            self.controller.close(mission_id, incomplete["evidence_id"], incomplete["sha256"])
        self.assertEqual(self.controller.get(mission_id)["status"], "RUNNING")

    def test_closes_with_real_evidence_store_hash_verification(self):
        from brain_v12.brain.evidence_store import EvidenceStore
        evidence_path = Path(self.tmp.name) / "evidence.sqlite3"
        store = EvidenceStore(str(evidence_path))
        try:
            controller = GoldenMissionController(
                str(Path(self.tmp.name) / "real-missions.sqlite3"),
                notifier=lambda mission, message: {"sent": False, "reason": "test"},
                evidence_store=store,
            )
            mission = controller.create(
                title="Real evidence store",
                objective="Verify objective against the actual SQLite evidence store",
                acceptance=["objective verified"],
            )
            controller.start(mission["mission_id"])
            payload = {
                "objective_verified": True,
                "acceptance_passed": True,
                "attempt_number": 1,
                "criteria_results": [{"criterion": "objective verified", "passed": True}],
            }
            evidence = store.append(mission["mission_id"], "objective-verification", payload, "test-verifier")
            result = controller.close(
                mission["mission_id"], evidence["evidence_id"], evidence["sha256"],
                "verified against real evidence store",
            )
            self.assertEqual(result["status"], "CLOSED")
            self.assertEqual(result["result"]["evidence_id"], evidence["evidence_id"])
            self.assertTrue(store.verify_hash(evidence["evidence_id"])["ok"])
        finally:
            store.close()

    def test_checkpoint_updates_estimate(self):
        self.controller.start(self.mission["mission_id"])
        m=self.controller.checkpoint(self.mission["mission_id"],"first step",25,next_estimate_minutes=20)
        self.assertEqual(m["status"],"RUNNING")
        self.assertEqual(m["attempts"],0)
        self.assertEqual(m["estimate_minutes"],20)

    def test_due_mission_reminder_sends_and_advances_schedule(self):
        from datetime import timedelta
        mission_id = self.mission["mission_id"]
        future = datetime.now(timezone.utc) + timedelta(minutes=5)
        result = self.controller.notify_due(now=future)
        self.assertEqual(result["checked"], 1)
        self.assertEqual(result["notifications_sent"], 0)
        self.assertEqual(result["notifications_failed_or_unconfigured"], 1)
        mission = self.controller.get(mission_id)
        self.assertTrue(any(e["event"] == "MISSION_UPDATE_REMINDER" for e in mission["evidence"]))
        self.assertGreater(datetime.fromisoformat(mission["next_update_at"]), future)

    def test_reminder_worker_tick_delegates_without_executing_objective(self):
        from brain_v12.brain.golden_mission_worker import GoldenMissionReminderWorker
        class Stub:
            def __init__(self): self.calls = 0
            def notify_due(self):
                self.calls += 1
                return {"checked": 0, "notifications_sent": 0, "notifications_failed_or_unconfigured": 0}
        stub = Stub()
        worker = GoldenMissionReminderWorker(stub, interval_seconds=1)
        self.assertEqual(worker.interval_seconds, 30)
        self.assertEqual(worker.tick()["checked"], 0)
        self.assertEqual(stub.calls, 1)

    def test_reminder_worker_start_is_idempotent_and_stop_joins_thread(self):
        import time
        from brain_v12.brain.golden_mission_worker import GoldenMissionReminderWorker

        class Stub:
            def __init__(self):
                self.calls = 0
                self.lock = __import__("threading").Lock()

            def notify_due(self):
                with self.lock:
                    self.calls += 1
                return {"checked": 0, "notifications_sent": 0,
                        "notifications_failed_or_unconfigured": 0}

        stub = Stub()
        worker = GoldenMissionReminderWorker(stub, interval_seconds=30)
        self.assertTrue(worker.start())
        self.assertFalse(worker.start())
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            with stub.lock:
                if stub.calls:
                    break
            time.sleep(0.01)
        before_stop = worker.status()
        self.assertTrue(before_stop["running"])
        self.assertIsNotNone(before_stop["started_at"])
        self.assertIsNotNone(before_stop["last_tick_at"])
        self.assertIsNone(before_stop["last_error"])
        self.assertEqual(before_stop["mode"], "REMINDERS_ONLY")
        worker.stop(timeout=1.0)
        self.assertFalse(worker._thread.is_alive())
        self.assertFalse(worker.status()["running"])
        self.assertGreaterEqual(stub.calls, 1)

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
