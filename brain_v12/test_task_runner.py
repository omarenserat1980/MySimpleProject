import unittest

from brain_v12.virtual_hardware.task_runner import BrainVMTaskRunner


class BrainVMTaskRunnerTests(unittest.TestCase):
    def test_two_tasks_interleave_and_keep_memory_isolated(self):
        runner = BrainVMTaskRunner(ram_cells=16, clock_width_bits=8)
        runner.create_task("alpha", [
            ("MOVI", 0, 11), ("STORE", 0, 2), ("LOAD", 1, 2),
            ("OUT", 1), ("HALT",),
        ])
        runner.create_task("beta", [
            ("MOVI", 0, 22), ("STORE", 0, 2), ("LOAD", 1, 2),
            ("OUT", 1), ("HALT",),
        ])

        result = runner.run(max_ticks=20)
        self.assertTrue(result["completed"])
        self.assertEqual(result["ticks_this_run"], 10)
        tasks = {task["name"]: task for task in result["tasks"]}
        self.assertEqual(tasks["alpha"]["output"], [11])
        self.assertEqual(tasks["beta"]["output"], [22])
        self.assertEqual(tasks["alpha"]["ram"]["nonzero"]["2"], 11)
        self.assertEqual(tasks["beta"]["ram"]["nonzero"]["2"], 22)
        self.assertEqual(tasks["alpha"]["instructions_executed"], 5)
        self.assertEqual(tasks["beta"]["instructions_executed"], 5)
        self.assertFalse(result["physical_hardware"])
        self.assertFalse(result["native_code_execution"])

    def test_budget_leaves_nonterminating_task_active(self):
        runner = BrainVMTaskRunner()
        runner.create_task("loop", [("JMP", 0)])
        result = runner.run(max_ticks=3)
        self.assertFalse(result["completed"])
        self.assertEqual(result["ticks_this_run"], 3)
        self.assertEqual(result["active_tasks"], ["loop"])

    def test_rejects_invalid_program_and_budget(self):
        runner = BrainVMTaskRunner()
        with self.assertRaisesRegex(ValueError, "NONEMPTY"):
            runner.create_task("empty", [])
        runner.create_task("valid", [("HALT",)])
        with self.assertRaisesRegex(ValueError, "BUDGET"):
            runner.run(max_ticks=0)

    def test_halted_task_is_terminated_and_not_scheduled_again(self):
        runner = BrainVMTaskRunner()
        runner.create_task("done", [("HALT",)])
        result = runner.run(max_ticks=5)
        self.assertTrue(result["completed"])
        self.assertEqual(result["ticks_this_run"], 1)
        self.assertEqual(result["tasks"][0]["state"], "TERMINATED")


if __name__ == "__main__":
    unittest.main()
