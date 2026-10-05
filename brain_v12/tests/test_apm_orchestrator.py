import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.apm_orchestrator import APMOrchestrator


class APMOrchestratorTests(unittest.TestCase):
    def test_checkpoint_and_resume_skip_completed_units(self):
        with tempfile.TemporaryDirectory() as td:
            state = str(Path(td) / "checkpoint.json")
            orch = APMOrchestrator(state)
            cp = orch.decide(
                run_id="run-1",
                runner_status="running",
                current_stage="VIDEO",
                completed=["S1", "S2"],
                failed=["S3"],
                blocked=[],
                cached=["S0"],
            )
            self.assertEqual(cp.status, "FAILED")
            resumed = orch.resume()
            self.assertEqual(resumed["resume_units"], ["S3"])
            self.assertEqual(resumed["skip_units"], ["S1", "S2", "S0"])

    def test_queued_runner_is_resume_later(self):
        with tempfile.TemporaryDirectory() as td:
            orch = APMOrchestrator(str(Path(td) / "checkpoint.json"))
            cp = orch.decide(
                run_id="run-2", runner_status="queued",
                current_stage="VIDEO", completed=[], failed=[], blocked=[], cached=[],
            )
            self.assertEqual(cp.status, "WAITING_FOR_RUNNER")
            self.assertEqual(cp.next_action, "RESUME_WHEN_RUNNER_AVAILABLE")


if __name__ == "__main__":
    unittest.main()
