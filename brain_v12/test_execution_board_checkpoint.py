import copy
import unittest

from brain_v12.virtual_hardware.execution_board import BrainVMExecutionBoard


class BrainVMCheckpointTests(unittest.TestCase):
    def test_checkpoint_restore_resumes_same_program_deterministically(self):
        program = [
            ("MOVI", 0, 21),
            ("STORE", 0, 4),
            ("LOAD", 1, 4),
            ("OUT", 1),
            ("HALT",),
        ]
        original = BrainVMExecutionBoard(ram_cells=32, clock_width_bits=8)
        original.step(program)
        original.step(program)
        checkpoint = original.checkpoint()

        resumed = BrainVMExecutionBoard(ram_cells=32)
        status = resumed.restore_checkpoint(checkpoint)
        self.assertEqual(status["cpu_pc"], original.cpu.pc)
        self.assertEqual(status["clock"]["ticks"], 2)
        result = resumed.run(program)
        self.assertEqual(result["cpu"]["output"], [21])
        self.assertEqual(result["clock"]["ticks"], 5)
        self.assertEqual(result["ram"]["nonzero"]["4"], 21)
        self.assertFalse(result["physical_hardware"])

    def test_restore_rejects_wrong_schema_without_mutating_board(self):
        board = BrainVMExecutionBoard(ram_cells=16)
        board.step([("MOVI", 0, 7), ("HALT",)])
        before = board.status()
        with self.assertRaisesRegex(ValueError, "SCHEMA_UNSUPPORTED"):
            board.restore_checkpoint({"schema": "unknown"})
        self.assertEqual(board.status(), before)

    def test_restore_rejects_invalid_register_state(self):
        board = BrainVMExecutionBoard(ram_cells=16)
        checkpoint = copy.deepcopy(board.checkpoint())
        checkpoint["cpu"]["registers"] = [1, 2]
        with self.assertRaisesRegex(ValueError, "CPU_OR_CLOCK_INVALID"):
            board.restore_checkpoint(checkpoint)

    def test_restore_rejects_ram_size_mismatch(self):
        source = BrainVMExecutionBoard(ram_cells=32)
        checkpoint = source.checkpoint()
        target = BrainVMExecutionBoard(ram_cells=16)
        with self.assertRaisesRegex(ValueError, "RAM_SIZE_MISMATCH"):
            target.restore_checkpoint(checkpoint)


if __name__ == "__main__":
    unittest.main()
