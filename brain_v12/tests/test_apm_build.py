import tempfile
import unittest

from brain_v12.brain.apm_build import BrainAPMBuild
from brain_v12.brain.parallel_stage_scheduler import Stage


class APMBuildTests(unittest.TestCase):
    def test_runs_through_execution_coordinator(self):
        stages = [
            Stage("A", metadata={"objective": "build A"}),
            Stage("B", metadata={"objective": "build B"}),
            Stage("C", depends_on=("A", "B"), metadata={"objective": "build C"}),
        ]
        executed = []

        def executor(stage):
            executed.append(stage.id)
            return {"ok": True, "stage": stage.id}

        def verifier(stage, result):
            return {"verified": True, "evidence_ref": f"evidence://{stage.id}"}

        with tempfile.TemporaryDirectory() as td:
            result = BrainAPMBuild(max_workers=2, retry_limit=0).run(
                stages, td, executor, verifier
            )

        self.assertEqual(result["status"], "VERIFIED_COMPLETED")
        self.assertEqual(result["apm_status"], "VERIFIED_COMPLETED")
        self.assertEqual(set(executed), {"A", "B", "C"})


if __name__ == "__main__":
    unittest.main()
