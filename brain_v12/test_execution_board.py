import unittest

from brain_v12.virtual_hardware.execution_board import BrainVMExecutionBoard


class BrainVMExecutionBoardTests(unittest.TestCase):
    def test_cpu_ram_and_clock_execute_one_program_together(self):
        board = BrainVMExecutionBoard(ram_cells=32, clock_width_bits=8)
        program = [
            ("MOVI", 0, 21),
            ("STORE", 0, 4),
            ("LOAD", 1, 4),
            ("OUT", 1),
            ("HALT",),
        ]
        result = board.run(program)
        self.assertTrue(result["ok"])
        self.assertEqual(result["mode"], "SIMULATED_BRAINVM_BOARD")
        self.assertEqual(result["instructions_executed_this_run"], 5)
        self.assertEqual(result["clock"]["ticks"], 5)
        self.assertEqual(result["cpu"]["output"], [21])
        self.assertEqual(result["ram"]["nonzero"]["4"], 21)
        self.assertFalse(result["physical_hardware"])

    def test_board_rejects_invalid_memory_and_instruction_budget(self):
        with self.assertRaisesRegex(ValueError, "RAM_CELLS"):
            BrainVMExecutionBoard(ram_cells=0)
        board = BrainVMExecutionBoard(ram_cells=16)
        with self.assertRaisesRegex(ValueError, "BUDGET_MUST_BE_POSITIVE"):
            board.run([("HALT",)], max_instructions=0)

    def test_non_terminating_program_hits_budget_without_claiming_success(self):
        board = BrainVMExecutionBoard(ram_cells=16)
        with self.assertRaisesRegex(RuntimeError, "BUDGET_EXHAUSTED"):
            board.run([("JMP", 0)], max_instructions=3)
        self.assertEqual(board.clock.ticks, 3)
        self.assertEqual(board.instructions_executed, 3)


if __name__ == "__main__":
    unittest.main()
