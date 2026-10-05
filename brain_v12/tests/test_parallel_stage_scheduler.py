import tempfile
import unittest
from brain_v12.brain.parallel_stage_scheduler import APMBuildOrchestrator, ParallelStageScheduler, Stage


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


    def test_independent_stages_can_share_workers_without_default_resource_lock(self):
        stages = [Stage("A"), Stage("B")]
        executed = []

        def execute(stage):
            executed.append(stage.id)
            return {"ok": True}

        def verify(stage, result):
            return {"verified": True, "evidence_ref": f"evidence://{stage.id}"}

        with tempfile.TemporaryDirectory() as td:
            result = ParallelStageScheduler(stages, td, max_workers=2).run(execute, verify)

        self.assertEqual(result["status"], "VERIFIED_COMPLETED")
        self.assertEqual(set(executed), {"A", "B"})

    def test_failed_dependency_blocks_downstream_stage(self):
        stages = [Stage("A"), Stage("B", depends_on=("A",))]
        executed = []

        def execute(stage):
            executed.append(stage.id)
            return {"ok": False}

        def verify(stage, result):
            return {"verified": False, "reason": "forced"}

        with tempfile.TemporaryDirectory() as td:
            result = ParallelStageScheduler(stages, td, retry_limit=0).run(execute, verify)

        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["blocked"], ["A", "B"])
        self.assertEqual(executed, ["A"])

    def test_cycle_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                ParallelStageScheduler(
                    [Stage("A", depends_on=("B",)), Stage("B", depends_on=("A",))], td
                )

    def test_apm_final_gate_can_reject_completed_stages(self):
        stages = [Stage("A")]

        def execute(stage):
            return {"ok": True}

        def verify(stage, result):
            return {"verified": True, "evidence_ref": "evidence://A"}

        with tempfile.TemporaryDirectory() as td:
            scheduler = ParallelStageScheduler(stages, td)
            result = APMBuildOrchestrator(scheduler).run(
                execute, verify, lambda result: {"verified": False, "reason": "gate"}
            )

        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["apm_status"], "FINAL_GATE_FAILED")


if __name__ == "__main__":
    unittest.main()
