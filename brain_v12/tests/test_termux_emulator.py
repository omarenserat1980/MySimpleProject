import unittest

from brain_v12.brain.termux_emulator import TermuxEmulator


class TermuxEmulatorTests(unittest.TestCase):
    def test_simulation_never_claims_real_execution(self):
        result = TermuxEmulator().simulate(["pkg", "install", "python"])
        self.assertTrue(result["ok"])
        self.assertEqual(result["reality_level"], "SIMULATED")
        self.assertFalse(result["executed"])
        self.assertIn("no Android shell", result["simulated_output"])

    def test_invalid_command_is_rejected(self):
        result = TermuxEmulator().simulate(["echo", "\x00"])
        self.assertFalse(result["ok"])
        self.assertFalse(result["executed"])


if __name__ == "__main__":
    unittest.main()
