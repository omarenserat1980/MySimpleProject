import unittest

from brain_v12.path_engine import (
    GateDecision,
    GateResult,
    PathEngine,
    PathSpec,
    PathState,
)


class PathEngineTests(unittest.TestCase):
    def test_happy_path_collects_evidence(self):
        calls = []

        def execute(run, step):
            calls.append(step)
            return {"ok": True, "step": step}

        engine = PathEngine(executor=execute)
        run = engine.start(
            PathSpec("diagnosis", "runtime-health", ["observe", "verify"]),
            "run-1",
        )

        engine.advance("run-1")
        engine.advance("run-1")

        self.assertEqual(run.state, PathState.SUCCEEDED)
        self.assertEqual(calls, ["observe", "verify"])
        self.assertTrue(any(e.kind == "verification" for e in run.evidence))
        self.assertTrue(any(e.kind == "complete" for e in run.evidence))

    def test_one_active_run_per_goal(self):
        engine = PathEngine(executor=lambda run, step: True)
        spec = PathSpec("repair", "same-goal", ["repair"])
        engine.start(spec, "run-1")
        with self.assertRaises(RuntimeError):
            engine.start(spec, "run-2")

    def test_authorization_can_block(self):
        def deny(_):
            return GateResult(GateDecision.DENY, "approval required")

        engine = PathEngine(
            authorization_gate=deny,
            executor=lambda run, step: True,
        )
        run = engine.start(PathSpec("publish", "publish-goal", ["upload"]), "run-1")
        engine.advance("run-1")
        self.assertEqual(run.state, PathState.BLOCKED)
        self.assertEqual(run.last_error, "approval required")

    def test_attempt_budget_stops_repeated_failures(self):
        def execute(_run, _step):
            raise RuntimeError("broken")

        engine = PathEngine(executor=execute)
        run = engine.start(
            PathSpec("repair", "broken-runtime", ["repair"], max_attempts=2),
            "run-1",
        )
        engine.advance("run-1")
        engine.advance("run-1")
        self.assertEqual(run.state, PathState.STOPPED)
        self.assertEqual(run.attempts, 2)
        self.assertTrue(any(e.kind == "failure" for e in run.evidence))


if __name__ == "__main__":
    unittest.main()
