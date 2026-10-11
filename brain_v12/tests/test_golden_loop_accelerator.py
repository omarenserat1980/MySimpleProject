import json
import tempfile
import unittest
from pathlib import Path

from brain_v12.tools.golden_loop_accelerator import inspect, passed


class GoldenLoopAcceleratorTests(unittest.TestCase):
    def test_missing_evidence_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = inspect(Path(tmp))
        self.assertEqual(report["status"], "GOLDEN_LOOP_BLOCKED")
        self.assertEqual(len(report["blockers_in_priority_order"]), 5)
        self.assertFalse(report["safety"]["missing_evidence_means_pass"])

    def test_runner_requires_all_three_runtime_signals(self):
        self.assertFalse(passed("runner", {
            "health": "NOT_VERIFIED", "online": False,
            "execution_probe": "skipped", "runtime_surface": "skipped",
        }))
        self.assertTrue(passed("runner", {
            "health": "VERIFIED", "online": True,
            "execution_probe": "PASS", "runtime_surface": "PASS",
        }))

    def test_executor_must_be_attested(self):
        self.assertFalse(passed("executor", {"verified": False, "executor_id": "arkan"}))
        self.assertTrue(passed("executor", {"verified": True, "executor_id": "arkan"}))

    def test_boot_requires_windows_2025_and_boot_time(self):
        base = {"boot_verified": True, "caption": "Windows Server 2025 Datacenter"}
        self.assertFalse(passed("boot", base))
        self.assertTrue(passed("boot", {**base, "boot_time": "2026-10-11T08:00:00Z"}))
        self.assertTrue(passed("boot", {
            "status": "WINDOWS_BOOT_VERIFIED",
            "guest": {
                "os": "Windows Server 2025", "os_caption": "Microsoft Windows Server 2025 Datacenter",
                "boot_verified": True, "boot_time": "2026-10-11T08:00:00Z"
            }
        }))
        self.assertFalse(passed("boot", {
            "boot_verified": True, "caption": "Windows 11", "boot_time": "2026-10-11T08:00:00Z"
        }))

    def test_completion_requires_exact_verified_status(self):
        self.assertFalse(passed("completion", {"status": "INCOMPLETE"}))
        self.assertTrue(passed("completion", {"status": "WINDOWS_BOOT_VERIFIED", "reasons": []}))
        self.assertFalse(passed("completion", {"status": "WINDOWS_BOOT_VERIFIED", "reasons": ["wrong disk"]}))

    def test_expected_run_id_rejects_cross_run_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "cloud-executor-gate.json").write_text(json.dumps({
                "verified": True, "executor_id": "arkan", "workflow_run_id": "100"
            }))
            report = inspect(root, expected_run_id="200")
        self.assertEqual(report["gates"]["executor"]["status"], "BLOCKED")
        self.assertIn("EXPECTED_RUN_ID_MISMATCH", [
            item["reason"] for item in report["blockers_in_priority_order"]
        ])

    def test_malformed_json_is_not_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "windows-completion-gate.json").write_text("{")
            report = inspect(Path(tmp))
        self.assertEqual(report["gates"]["completion"]["status"], "BLOCKED")
        self.assertEqual(report["gates"]["completion"]["selected"]["parse_error"], "JSONDecodeError")

    def test_report_does_not_claim_side_effects(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = inspect(Path(tmp))
        self.assertTrue(report["safety"]["read_only"])
        self.assertFalse(report["safety"]["changed_secrets"])
        self.assertFalse(report["safety"]["started_vm_or_cloud_resource"])


if __name__ == "__main__":
    unittest.main()
