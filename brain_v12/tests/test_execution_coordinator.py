import unittest

from brain_v12.brain.execution_coordinator import BrainExecutionCoordinator


class ExecutionCoordinatorTests(unittest.TestCase):
    def test_verified_completion_updates_both_engines(self):
        c = BrainExecutionCoordinator()
        created = c.create("inspect repository", max_attempts=2)
        cid = created["control"]["id"]

        result = c.execute(
            cid,
            lambda objective: {"ok": True, "objective": objective},
            lambda value: {"verified": True, "evidence_ref": "evidence://run/1"},
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "VERIFIED_COMPLETED")
        self.assertEqual(result["task"]["status"], "COMPLETED")
        self.assertEqual(result["task"]["evidence_ref"], "evidence://run/1")

    def test_failed_verification_enters_bounded_retry(self):
        c = BrainExecutionCoordinator()
        cid = c.create("repair build", max_attempts=2)["control"]["id"]

        result = c.execute(
            cid,
            lambda _: {"ok": False},
            lambda _: {"verified": False, "evidence_ref": "evidence://run/2"},
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "RETRYING")
        self.assertEqual(result["task"]["status"], "RETRYING")

    def test_repair_callback_is_evidence_recorded(self):
        c = BrainExecutionCoordinator()
        cid = c.create("repair test", max_attempts=2)["control"]["id"]
        calls = []

        result = c.execute(
            cid,
            lambda _: {"ok": False},
            lambda _: {"verified": False},
            repair=lambda failure: calls.append(failure["error"]) or {"ok": True, "action": "reset"},
        )

        self.assertEqual(calls, ["VERIFICATION_FAILED"])
        self.assertEqual(result["repair"]["action"], "reset")
        self.assertTrue(any(e["stage"] == "repair" for e in result["control"]["evidence"]))

    def test_unknown_task_never_executes(self):
        c = BrainExecutionCoordinator()
        called = []
        result = c.execute(
            "missing",
            lambda _: called.append(True) or {},
            lambda _: {"verified": True, "evidence_ref": "evidence://bad"},
        )
        self.assertFalse(result["ok"])
        self.assertEqual(called, [])
        self.assertEqual(result["error"], "TASK_NOT_FOUND")
