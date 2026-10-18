"""Contract tests for the bounded Ramulator 2.1 Python adapter."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from brain_v12.hardware import ramulator_adapter as adapter


class RamulatorAdapterTests(unittest.TestCase):
    def test_missing_python_fails_closed(self):
        with mock.patch.object(adapter.shutil, "which", return_value=None):
            result = adapter.run_script("not-used.py")
        self.assertEqual(result["status"], "NOT_CONFIGURED")
        self.assertFalse(result["physical_hardware_verified"])

    def test_timeout_bounds_are_enforced(self):
        for value in (0, 301, True, "3"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                adapter.run_script("unused.py", timeout_seconds=value)

    def test_script_must_be_python_file(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.yaml"
            config.write_text("not python", encoding="utf-8")
            with mock.patch.object(adapter.shutil, "which", return_value="/usr/bin/python3"):
                with self.assertRaises(ValueError):
                    adapter.run_script(str(config))

    def test_success_hashes_script_and_never_claims_physical_ram(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "example.py"
            script.write_text("print('simulated')\n", encoding="utf-8")
            with mock.patch.object(adapter.shutil, "which", return_value="/usr/bin/python3"):
                with mock.patch.object(adapter.subprocess, "run", return_value=mock.Mock(
                    returncode=0, stdout="simulated", stderr=""
                )) as run:
                    result = adapter.run_script(str(script))
        self.assertFalse(run.call_args.kwargs["shell"])
        self.assertEqual(result["status"], "SIMULATION_COMPLETED")
        self.assertEqual(len(result["script_sha256"]), 64)
        self.assertEqual(result["evidence_class"], "SIMULATED")
        self.assertFalse(result["physical_hardware_verified"])

    def test_nonzero_exit_is_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "example.py"
            script.write_text("raise SystemExit(2)\n", encoding="utf-8")
            with mock.patch.object(adapter.shutil, "which", return_value="/usr/bin/python3"):
                with mock.patch.object(adapter.subprocess, "run", return_value=mock.Mock(
                    returncode=2, stdout="", stderr="failed"
                )):
                    result = adapter.run_script(str(script))
        self.assertEqual(result["status"], "SIMULATION_FAILED")
        self.assertFalse(result["physical_hardware_verified"])

    def test_evidence_json_is_deterministic(self):
        payload = {"status": "SIMULATED", "physical_hardware_verified": False}
        self.assertEqual(
            adapter.evidence_json(payload),
            json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        )


if __name__ == "__main__":
    unittest.main()
