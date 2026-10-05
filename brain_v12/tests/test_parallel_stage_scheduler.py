import tempfile
import unittest
from brain_v12.brain.parallel_stage_scheduler import ParallelStageScheduler, Stage


class ParallelStageSchedulerTests(unittest.TestCase):
    def test_independent_stages_and_dependencies(self):
        stages = [Stage("A"), Stage("B"), Stage("C", depends_on=("A",))]
        calls = []

        def execute(stage):
            calls.append(stage.id)
            return {"ok": True}

        def verify(stage, result):
            return {"verified": True, "evidence_ref": f"evidence://{stage.id}"}

        with tempfile.TemporaryDirectory() as td:
            result = ParallelStageScheduler(stages, td, max_workers=2).run(execute, verify)

        self.assertEqual(result["status"], "VERIFIED_COMPLETED")
        self.assertEqual(set(calls), {"A", "B", "C"})

    def test_failed_stage_retries_locally(self):
        stages = [Stage("A"), Stage("B", depends_on=("A",))]
        attempts = {"A": 0, "B": 0}

        def execute(stage):
            attempts[stage.id] += 1
            return {"ok": attempts[stage.id] >= 2}

        def verify(stage, result):
            return {"verified": result["ok"], "evidence_ref": f"evidence://{stage.id}"}

        with tempfile.TemporaryDirectory() as td:
            result = ParallelStageScheduler(
                stages, td, max_workers=2, retry_limit=1).run(execute, verify)

        self.assertEqual(result["status"], "VERIFIED_COMPLETED")
        self.assertEqual(attempts["A"], 2)
        self.assertEqual(attempts["B"], 1)

    def test_verified_cache_skips_rebuild(self):
        stages = [Stage("A", input_fingerprint="v1")]
        executed = []

        def execute(stage):
            executed.append(stage.id)
            return {"ok": True}

        def verify(stage, result):
            return {"verified": True, "evidence_ref": "evidence://A"}

        with tempfile.TemporaryDirectory() as td:
            ParallelStageScheduler(stages, td).run(execute, verify)
            result = ParallelStageScheduler(stages, td).run(execute, verify)

        self.assertEqual(result["status"], "VERIFIED_COMPLETED")
        self.assertEqual(executed, ["A"])


if __name__ == "__main__":
    unittest.main()
