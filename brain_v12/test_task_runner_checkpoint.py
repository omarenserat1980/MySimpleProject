"""Checkpoint/resume tests for the simulation-only BrainVM task runner."""
import copy
import unittest

from brain_v12.virtual_hardware.task_runner import BrainVMTaskRunner


class TaskRunnerCheckpointTests(unittest.TestCase):
    def test_programs_and_execution_state_resume_deterministically(self):
        program = [("MOVI", 0, 7), ("OUT", 0), ("JMP", 2)]
        original = BrainVMTaskRunner(ram_cells=32)
        original.create_task("worker", program)
        original.run(max_ticks=5)
        snapshot = original.checkpoint()

        resumed = BrainVMTaskRunner()
        resumed.restore_checkpoint(snapshot)
        self.assertEqual(resumed.checkpoint(), snapshot)
        first = original.run(max_ticks=9)
        second = resumed.run(max_ticks=9)
        self.assertEqual(first["trace"], second["trace"])
        self.assertEqual(first["tasks"], second["tasks"])
        self.assertEqual(first["total_ticks"], second["total_ticks"])

    def test_halted_task_and_process_identity_survive_restore(self):
        original = BrainVMTaskRunner(ram_cells=16)
        pid = original.create_task("short", [("MOVI", 0, 3), ("HALT",)])
        original.run(max_ticks=10)
        snapshot = original.checkpoint()
        resumed = BrainVMTaskRunner()
        resumed.restore_checkpoint(snapshot)
        task = resumed._tasks[pid]
        self.assertEqual(task["process"].state, "TERMINATED")
        self.assertTrue(task["board"].cpu.halted)
        self.assertEqual(resumed.kernel.processes[pid].name, "short")

    def test_bad_snapshot_is_rejected_without_mutating_runner(self):
        runner = BrainVMTaskRunner(ram_cells=16)
        runner.create_task("existing", [("JMP", 0)])
        before = runner.checkpoint()
        malformed = copy.deepcopy(before)
        malformed["tasks"][0]["steps"] += 1
        with self.assertRaisesRegex(ValueError, "STEP_COUNT_MISMATCH"):
            runner.restore_checkpoint(malformed)
        self.assertEqual(runner.checkpoint(), before)

    def test_program_must_be_included_and_safe_scalar_only(self):
        runner = BrainVMTaskRunner()
        runner.create_task("worker", [("JMP", 0)])
        snapshot = runner.checkpoint()
        snapshot["task_programs_included"] = False
        with self.assertRaisesRegex(ValueError, "PROGRAMS_INVALID"):
            runner.restore_checkpoint(snapshot)
        snapshot = runner.checkpoint()
        snapshot["tasks"][0]["program"][0][1] = {"unexpected": "object"}
        with self.assertRaisesRegex(ValueError, "INSTRUCTION_INVALID"):
            runner.restore_checkpoint(snapshot)


if __name__ == "__main__":
    unittest.main()
