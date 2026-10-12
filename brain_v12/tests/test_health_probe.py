import unittest

from brain_v12.brain.health_probe import HealthProbeEngine, command_probe


class HealthProbeTests(unittest.TestCase):
    def test_missing_probe_is_not_healthy(self):
        engine = HealthProbeEngine()
        result = engine.probe("missing")
        self.assertFalse(result.available)
        self.assertEqual(result.reason, "NO_PROBE_REGISTERED")

    def test_probe_exception_is_failure(self):
        engine = HealthProbeEngine()
        engine.register("broken", lambda: 1 / 0)
        result = engine.probe("broken")
        self.assertFalse(result.available)
        self.assertTrue(result.reason.startswith("PROBE_ERROR:"))

    def test_command_probe_does_not_claim_missing_command(self):
        engine = HealthProbeEngine()
        engine.register("definitely-missing", command_probe("brain-command-that-does-not-exist"))
        result = engine.probe("definitely-missing")
        self.assertFalse(result.available)


if __name__ == "__main__":
    unittest.main()
