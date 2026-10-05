import unittest

from brain_v12.brain.apm_execution_status import classify


class APMExecutionStatusTests(unittest.TestCase):
    def test_queued_is_runner_capacity_not_build_failure(self):
        result = classify("queued")
        self.assertEqual(result.status, "WAITING_FOR_RUNNER")
        self.assertEqual(result.execution_blocker, "RUNNER_CAPACITY")

    def test_success_is_verified(self):
        self.assertEqual(classify("completed", "success").status, "VERIFIED")

    def test_failure_is_execution_failure(self):
        self.assertEqual(classify("completed", "failure").status, "EXECUTION_FAILED")


if __name__ == "__main__":
    unittest.main()
