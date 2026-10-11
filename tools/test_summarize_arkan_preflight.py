#!/usr/bin/env python3
"""Regression tests for the Arkan preflight summarizer; uses only temporary fixtures."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SUMMARIZER = Path(__file__).with_name("summarize_arkan_preflight.py")


class SummarizerTests(unittest.TestCase):
    def run_summary(self, path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SUMMARIZER), str(path)],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_reports_not_boot_proof_and_detects_non_admin(self) -> None:
        report = {
            "schema": "brain.arkan.windows-real-boot-diagnostic.v2",
            "machine": "TEST-HOST",
            "generated_utc": "2026-10-11T00:00:00Z",
            "warnings": ["hyperv_host : type=UnauthorizedAccessException; category=PermissionDenied; id=TestId"],
            "checks": {
                "identity": {"User": "test", "IsAdministrator": False},
                "hyperv_module": [{"Name": "Hyper-V", "Version": "1.0", "Path": "test"}],
                "hyperv_commands": {"GetVM": True, "GetVMHost": True},
                "hyperv_host": None,
                "vms": [],
                "cpu_virtualization": [
                    {"VirtualizationFirmwareEnabled": False, "VMMonitorModeExtensions": True}
                ],
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            path.write_text(json.dumps(report), encoding="utf-8")
            result = self.run_summary(path)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("WINDOWS_BOOT_VERIFIED=false", result.stdout)
        self.assertIn("not elevated", result.stdout)
        self.assertIn("classified warning", result.stdout)
        self.assertIn("firmware flag is false", result.stdout)
        self.assertIn("diagnostic only", result.stdout)

    def test_handles_cpu_virtualization_as_single_object(self) -> None:
        report = {
            "machine": "TEST-HOST",
            "checks": {
                "cpu_virtualization": {"VirtualizationFirmwareEnabled": True},
                "hyperv_commands": {"GetVMHost": True},
            },
            "warnings": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            path.write_text(json.dumps(report), encoding="utf-8")
            result = self.run_summary(path)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("firmware flag reports enabled", result.stdout)

    def test_missing_file_returns_actionable_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_summary(Path(tmp) / "missing.json")
        self.assertEqual(result.returncode, 2)
        self.assertIn("report not found", result.stderr)

    def test_invalid_json_does_not_dump_file_contents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text("SECRET_SENTINEL {", encoding="utf-8")
            result = self.run_summary(path)
        self.assertEqual(result.returncode, 2)
        self.assertIn("JSONDecodeError", result.stderr)
        self.assertNotIn("SECRET_SENTINEL", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
