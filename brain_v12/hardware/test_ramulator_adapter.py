"""Contract tests for the bounded Ramulator adapter."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from brain_v12.hardware import ramulator_adapter as adapter


class RamulatorAdapterTests(unittest.TestCase):
    def test_missing_executable_fails_closed(self):
        with mock.patch.object(adapter.shutil, "which", return_value=None):
            result = adapter.run_config("not-used")
        self.assertEqual(result["status"], "NOT_CONFIGURED")
        self.assertFalse(result["physical_hardware_verified"])

    def test_timeout_bounds_are_enforced(self):
        with self.assertRaises(ValueError):
            adapter.run_config("unused", timeout_seconds=0)
        with self.assertRaises(ValueError):
            adapter.run_config("unused", timeout_seconds=301)

    def test_config_must_be_small_regular_file(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.yaml"
            config.write_text("Frontend: {}
", encoding="utf-8")
            with mock.patch.object(adapter.shutil, "which", return_value="/usr/bin/ramulator2"):
                with mock.patch.object(adapter.subprocess, "run", return_value=mock.Mock(
                    returncode=0, stdout="ok", stderr=""
                )):
                    result = adapter.run_config(str(config))
        self.assertEqual(result["status"], "SIMULATION_COMPLETED")
        self.assertEqual(len(result["config_sha256"]), 64)
        self.assertEqual(result["evidence_class"], "SIMULATED")
        self.assertFalse(result["physical_hardware_verified"])

    def test_command_does_not_use_shell_and_marks_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.yaml"
            config.write_text("Frontend: {}
", encoding="utf-8")
            with mock.patch.object(adapter.shutil, "which", return_value="/usr/bin/ramulator2"):
                with mock.patch.object(adapter.subprocess, "run", return_value=mock.Mock(
                    returncode=2, stdout="", stderr="bad config"
                )) as run:
                    result = adapter.run_config(str(config))
        self.assertFalse(run.call_args.kwargs["shell"])
        self.assertEqual(result["status"], "SIMULATION_FAILED")
        self.assertFalse(result["physical_hardware_verified"])

    def test_evidence_json_is_deterministic(self):
        payload = {"status": "SIMULATED", "physical_hardware_verified": False}
        self.assertEqual(adapter.evidence_json(payload), json.dumps(
            payload, sort_keys=True, separators=(",", ":")
        ) + "
")


if __name__ == "__main__":
    unittest.main()
