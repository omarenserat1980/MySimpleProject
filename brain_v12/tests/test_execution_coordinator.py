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
        self.assertEqual(result["path"]["state"], "SUCCEEDED")

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
        self.assertEqual(result["path"]["state"], "FAILED")
        self.assertEqual(result["path"]["attempts"], 1)

    def test_second_failure_stops_at_path_budget(self):
        c = BrainExecutionCoordinator()
        cid = c.create("bounded failure", max_attempts=2)["control"]["id"]
        execute = lambda _: {"ok": False}
        verify = lambda _: {"verified": False}

        first = c.execute(cid, execute, verify)
        second = c.execute(cid, execute, verify)

        self.assertEqual(first["status"], "RETRYING")
        self.assertFalse(second["ok"])
        self.assertEqual(second["control"]["status"], "FAILED")
        self.assertEqual(second["path"]["state"], "STOPPED")
        self.assertEqual(second["path"]["attempts"], 2)

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


    def test_full_multistep_path_requires_verified_progression(self):
        c = BrainExecutionCoordinator()
        created = c.create_multistep(
            "full build",
            ["inspect", "design", "implement", "test", "verify"],
            max_attempts=6,
        )
        path_id = created["path"]["run_id"]
        calls = []

        def executor_for(step):
            return lambda _: calls.append(step) or {"ok": True, "step": step}

        handlers = {step: executor_for(step) for step in ("inspect", "design", "implement", "test", "verify")}
        verifiers = {
            step: (lambda value: {"verified": True, "evidence_ref": f"evidence://{value['step']}"})
            for step in handlers
        }

        failed = c.execute_path_step(
            path_id,
            handlers,
            {**verifiers, "inspect": lambda _: {"verified": False}},
        )
        self.assertFalse(failed["ok"])
        self.assertEqual(failed["step"], "inspect")
        self.assertEqual(failed["path"]["step"], "inspect")
        self.assertEqual(calls, ["inspect"])

        states = []
        for expected in ("inspect", "design", "implement", "test", "verify"):
            result = c.execute_path_step(path_id, handlers, verifiers)
            states.append(result["path"]["state"])
            self.assertEqual(result["step"], expected)

        self.assertEqual(calls, ["inspect", "inspect", "design", "implement", "test", "verify"])
        self.assertEqual(states[-1], "SUCCEEDED")
        self.assertEqual(states[:-1], ["RUNNING", "RUNNING", "RUNNING", "RUNNING"])
        self.assertEqual(result["task"]["status"], "COMPLETED")
        self.assertIsNone(result["path"]["step"])

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


if __name__ == "__main__":
    unittest.main()
