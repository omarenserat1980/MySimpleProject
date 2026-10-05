import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain_v12.brain.execution_gateway import BrainExecutionGateway
from brain_v12.brain.internal_task_runtime import InternalTaskRuntime


class FakeRunner:
    def require(self, capability):
        return None

    def run(self, argv, cwd=None, timeout=None):
        class R:
            returncode = 0
            stdout = "OK"
            stderr = ""
        return R()


class InternalRuntimeTests(unittest.TestCase):
    def test_gateway_is_brain_internal_only(self):
        g = BrainExecutionGateway(FakeRunner())
        d = g.authorize("brain-internal-execution")
        self.assertEqual(d.executor, "brain-internal")
        self.assertTrue(d.verified)

    def test_runtime_survives_state_and_records_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            rt = InternalTaskRuntime(d, BrainExecutionGateway(FakeRunner()))
            item = rt.enqueue("test", ["python", "-c", "print('ok')"])
            result = rt.run_one()
            self.assertEqual(result["state"], "COMPLETED")
            self.assertEqual(rt.status()["pending"], 0)
            self.assertTrue(Path(result["evidence_ref"]).exists())
            self.assertEqual(rt.pending(), [])

    def test_runtime_blocks_if_internal_runner_is_unavailable(self):
        class OfflineRunner:
            def require(self, capability):
                raise RuntimeError("BRAIN_INTERNAL_RUNNER_NOT_VERIFIED")
        with tempfile.TemporaryDirectory() as d:
            rt = InternalTaskRuntime(d, BrainExecutionGateway(OfflineRunner()))
            rt.enqueue("blocked", ["echo", "x"])
            result = rt.run_one()
            self.assertEqual(result["state"], "BLOCKED")
            self.assertIn("BRAIN_INTERNAL_RUNNER_NOT_VERIFIED", result["error"])


if __name__ == "__main__":
    unittest.main()
