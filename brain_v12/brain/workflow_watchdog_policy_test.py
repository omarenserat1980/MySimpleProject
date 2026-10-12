import unittest

from brain_v12.brain.workflow_watchdog_policy import (
    partition_failures,
    recovery_allowed,
    select_recovery_candidates,
)


class WorkflowWatchdogPolicyTests(unittest.TestCase):
    def test_only_target_sha_is_eligible(self):
        rows = [
            {"run_id": 1, "head_sha": "target"},
            {"run_id": 2, "head_sha": "old"},
            {"run_id": 3, "head_sha": "target"},
        ]
        eligible, ignored = partition_failures(rows, "target")
        self.assertEqual([1, 3], [r["run_id"] for r in eligible])
        self.assertEqual([2], [r["run_id"] for r in ignored])

    def test_empty_target_is_fail_closed(self):
        rows = [{"run_id": 1, "head_sha": "target"}]
        eligible, ignored = partition_failures(rows, "")
        self.assertEqual([], eligible)
        self.assertEqual(rows, ignored)

    def test_global_recovery_selection_is_bounded(self):
        rows = [
            {"run_id": 1, "head_sha": "target", "attempt": 1, "created_at": "2026-10-08T00:00:00Z"},
            {"run_id": 2, "head_sha": "target", "attempt": 1, "created_at": "2026-10-08T00:01:00Z"},
            {"run_id": 3, "head_sha": "old", "attempt": 1, "created_at": "2026-10-08T00:02:00Z"},
        ]
        selected = select_recovery_candidates(rows, "target")
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["run_id"], 1)

    def test_recovery_guard_rejects_cross_sha(self):
        self.assertTrue(recovery_allowed({"head_sha": "target"}, "target"))
        self.assertFalse(recovery_allowed({"head_sha": "old"}, "target"))
        self.assertFalse(recovery_allowed({"head_sha": ""}, "target"))
        self.assertFalse(recovery_allowed({"head_sha": "target"}, ""))


if __name__ == "__main__":
    unittest.main()
