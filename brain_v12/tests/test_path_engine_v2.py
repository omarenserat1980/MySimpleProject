import unittest

from brain_v12.path_engine import GateDecision, GateResult, PathEngine, PathSpec, PathState


class MultiStepPathV2Tests(unittest.TestCase):
    def test_steps_advance_one_verified_step_at_a_time(self):
        calls = []
        engine = PathEngine(
            authorization_gate=lambda _: GateResult(GateDecision.ALLOW),
            policy_gate=lambda _: GateResult(GateDecision.ALLOW),
            executor=lambda run, step: calls.append(step) or {"step": step},
            verifier=lambda run, result: result["step"] == run.current_step,
        )
        run = engine.start(
            PathSpec("v2", "multi-step", ["inspect", "design", "implement"], max_attempts=3, max_steps=3),
            "v2-run",
        )

        engine.advance("v2-run")
        self.assertEqual(run.state, PathState.RUNNING)
        self.assertEqual(run.step_index, 1)
        self.assertEqual(calls, ["inspect"])

        engine.advance("v2-run")
        self.assertEqual(run.step_index, 2)
        self.assertEqual(calls, ["inspect", "design"])

        engine.advance("v2-run")
        self.assertEqual(run.state, PathState.SUCCEEDED)
        self.assertEqual(calls, ["inspect", "design", "implement"])

    def test_failed_step_does_not_skip_forward(self):
        engine = PathEngine(
            executor=lambda run, step: {"step": step},
            verifier=lambda run, result: False,
        )
        run = engine.start(PathSpec("v2", "bounded", ["inspect", "implement"], max_attempts=2, max_steps=2), "run")
        engine.advance("run")
        self.assertEqual(run.state, PathState.FAILED)
        self.assertEqual(run.step_index, 0)
        self.assertEqual(run.current_step, "inspect")
        engine.advance("run")
        self.assertEqual(run.state, PathState.STOPPED)
        self.assertEqual(run.step_index, 0)
        self.assertEqual(run.attempts, 2)

    def test_step_budget_cannot_be_smaller_than_plan(self):
        engine = PathEngine()
        with self.assertRaises(ValueError):
            engine.start(PathSpec("v2", "invalid", ["a", "b"], max_steps=1), "bad")


if __name__ == "__main__":
    unittest.main()
