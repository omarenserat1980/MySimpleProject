import unittest

from brain_v12.brain.execution_policy import (
    BRAIN_INTERNAL,
    WINDOWS_REAL_BOOT,
    Executor,
    choose_executor,
    default_executors,
)
from brain_v12.brain.internal_runner import InternalRunner


class InternalRunnerPolicyTests(unittest.TestCase):
    def test_internal_runner_declares_windows_capability(self):
        runner = InternalRunner()
        self.assertIn("windows-server-2025-real-boot", runner.capabilities())
        self.assertIn("brain-internal-execution", runner.capabilities())

    def test_internal_executor_wins(self):
        selected = choose_executor(default_executors(), WINDOWS_REAL_BOOT)
        self.assertEqual(selected.name, BRAIN_INTERNAL)
        self.assertFalse(selected.external)

    def test_external_runtime_fallback_is_forbidden(self):
        with self.assertRaisesRegex(RuntimeError, "EXTERNAL_EXECUTOR_FORBIDDEN"):
            choose_executor(
                [Executor(
                    name="github-ci",
                    capabilities=frozenset({WINDOWS_REAL_BOOT}),
                    priority=0,
                    external=True,
                )],
                WINDOWS_REAL_BOOT,
            )


if __name__ == "__main__":
    unittest.main()
