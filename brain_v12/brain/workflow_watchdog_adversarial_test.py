import json
import unittest

from brain_v12.brain.workflow_watchdog_policy import partition_failures, recovery_allowed


class WorkflowWatchdogAdversarialTests(unittest.TestCase):
    def test_mixed_sha_recovery_is_fail_closed(self):
        target_sha = "a" * 40
        old_sha = "b" * 40
        rows = [
            {"run_id": 1001, "head_sha": target_sha},
            {"run_id": 1002, "head_sha": old_sha},
        ]

        eligible, ignored = partition_failures(rows, target_sha)

        self.assertEqual([1001], [row["run_id"] for row in eligible])
        self.assertEqual([1002], [row["run_id"] for row in ignored])
        self.assertTrue(recovery_allowed(eligible[0], target_sha))
        self.assertFalse(recovery_allowed(ignored[0], target_sha))

    def test_malformed_or_missing_sha_is_never_recoverable(self):
        target_sha = "a" * 40
        rows = [
            {"run_id": 2001},
            {"run_id": 2002, "head_sha": ""},
            {"run_id": 2003, "head_sha": "b" * 40},
        ]

        eligible, ignored = partition_failures(rows, target_sha)

        self.assertEqual([], eligible)
        self.assertEqual([2001, 2002, 2003], [row["run_id"] for row in ignored])
        self.assertTrue(all(not recovery_allowed(row, target_sha) for row in rows))


if __name__ == "__main__":
    unittest.main()
