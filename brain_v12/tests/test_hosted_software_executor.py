from __future__ import annotations

import tempfile
import unittest

from brain_v12.brain.hosted_software_executor import HostedSoftwareExecutor, run_bounded_task


class HostedSoftwareExecutorTests(unittest.TestCase):
    def test_identity_and_truth_boundary_are_not_arkan_host_claims(self):
        with tempfile.TemporaryDirectory() as root:
            executor = HostedSoftwareExecutor(root=root)
            try:
                status = executor.status()
                self.assertEqual(status["node"]["id"], "brain-hosted-ci-01")
                self.assertEqual(status["runtime_mode"], "EPHEMERAL_CI_JOB")
                self.assertEqual(status["reality"], "SIMULATED")
                self.assertFalse(status["windows_server_2025"]["native_os_boot_verified"])
                self.assertFalse(status["desktop_commander_required"])
            finally:
                executor.close()

    def test_only_allowlisted_symbolic_tasks_are_admitted(self):
        with tempfile.TemporaryDirectory() as root:
            executor = HostedSoftwareExecutor(root=root)
            try:
                with self.assertRaisesRegex(ValueError, "TASK_TYPE_NOT_ALLOWED"):
                    executor.submit("shell")
            finally:
                executor.close()

    def test_bounded_smoke_reports_simulation_not_native_windows_boot(self):
        report = run_bounded_task("cpu_smoke", timeout_seconds=20)
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["node"]["id"], "brain-hosted-ci-01")
        self.assertEqual(report["reality"], "SIMULATED")
        self.assertFalse(report["windows_server_2025"]["native_os_boot_verified"])


if __name__ == "__main__":
    unittest.main()
