import unittest

from brain_v12.design_factory.execution import initialize_execution, execute_next_step
from brain_v12.design_factory.plan import prepare_design_plan


class BoundedExecutionTests(unittest.TestCase):
    def setUp(self):
        self.plan = prepare_design_plan("Bitcoin ASIC RTL and OpenROAD physical design verification")
        self.state = initialize_execution(self.plan)

    def test_default_is_plan_only_and_does_not_call_executor(self):
        calls = []
        result = execute_next_step(self.state, lambda step: calls.append(step), authorize=True)
        self.assertEqual(calls, [])
        self.assertEqual(result["steps"][0]["status"], "PLANNED")
        self.assertFalse(result["execution_started"])
        self.assertFalse(result["steps"][0]["evidence"]["execution_performed"])
        self.assertEqual(result["next_step_index"], 0)

    def test_execution_without_explicit_authorization_is_blocked(self):
        calls = []
        result = execute_next_step(
            self.state, lambda step: calls.append(step), authorize=False, dry_run=False
        )
        self.assertEqual(calls, [])
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["steps"][0]["evidence"]["reason"],
                         "EXPLICIT_AUTHORIZATION_REQUIRED")

    def test_missing_executor_fails_closed(self):
        result = execute_next_step(self.state, authorize=True, dry_run=False)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["steps"][0]["evidence"]["reason"], "BLOCKED_NO_EXECUTOR")
        self.assertTrue(result["stopped"])

    def test_one_call_dispatches_at_most_one_step(self):
        calls = []
        result = execute_next_step(
            self.state,
            lambda step: calls.append(step) or {
                "status": "SIMULATED", "evidence": {"source": "unit-test"}
            },
            authorize=True,
            dry_run=False,
        )
        self.assertEqual(len(calls), 1)
        self.assertEqual(sum(step["started"] for step in result["steps"]), 1)
        self.assertEqual(result["next_step_index"], 1)
        self.assertEqual(result["steps"][0]["status"], "SIMULATED")
        self.assertTrue(all(step["status"] == "PLANNED" for step in result["steps"][1:]))

    def test_failure_stops_plan_and_next_call_cannot_continue(self):
        result = execute_next_step(
            self.state,
            lambda step: {"status": "FAILED", "evidence": {"reason": "synthetic failure"}},
            authorize=True,
            dry_run=False,
        )
        self.assertTrue(result["stopped"])
        self.assertEqual(result["status"], "FAILED")
        later = execute_next_step(
            result,
            lambda step: self.fail("executor must not be called after failure"),
            authorize=True,
            dry_run=False,
        )
        self.assertTrue(later["stopped"])
        self.assertEqual(later["next_step_index"], 1)

    def test_executor_cannot_promote_result_to_verified(self):
        result = execute_next_step(
            self.state,
            lambda step: {"status": "VERIFIED", "evidence": {"source": "synthetic"}},
            authorize=True,
            dry_run=False,
        )
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["steps"][0]["status"], "FAILED")
        self.assertFalse(any(step["status"] == "VERIFIED" for step in result["steps"]))

    def test_invalid_executor_output_stops_execution(self):
        result = execute_next_step(
            self.state, lambda step: {"status": "TESTED"}, authorize=True, dry_run=False
        )
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["steps"][0]["evidence"]["kind"], "EXECUTOR_ERROR")


if __name__ == "__main__":
    unittest.main()
