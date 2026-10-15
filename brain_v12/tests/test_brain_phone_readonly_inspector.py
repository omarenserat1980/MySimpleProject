"""Safety tests for the read-only local resource inspector."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain_v12.tools.brain_phone_readonly_inspector import (
    inspect_local_resources,
    write_json_atomically,
)


class ReadOnlyInspectorTests(unittest.TestCase):
    @patch("brain_v12.tools.brain_phone_readonly_inspector.collect_resource_snapshot")
    def test_reports_local_metrics_without_claiming_verification(self, collect):
        collect.return_value = {
            "observed_at_utc": "2026-10-15T00:00:00+00:00", "os": "Linux",
            "os_release": "test", "architecture": "aarch64", "python_version": "3.x",
            "cpu_logical_count": 8, "available_memory_bytes": 1024,
            "disk": {"free_bytes": 2048}, "load_average_1_5_15": None,
        }
        r = inspect_local_resources("test-phone")
        self.assertEqual(r["mode"], "READ_ONLY_LOCAL_MEASUREMENT")
        self.assertEqual(r["state"], "MEASURED_LOCAL_UNVERIFIED")
        self.assertFalse(r["synthetic"])
        self.assertEqual(r["measurement_source"], "LOCAL_OS_SELF_REPORTED")
        self.assertTrue(r["resource_metrics_are_self_reported"])
        for key in ("device_identity_verified", "independent_hardware_attestation",
                    "network_calls_performed", "heartbeat_sent", "device_registered",
                    "activation_performed", "tasks_dispatched", "mining_started",
                    "pool_connection_attempted", "mining_verified", "revenue_verified"):
            self.assertFalse(r[key], key)
        collect.assert_called_once_with()

    def test_rejects_invalid_node_id(self):
        with self.assertRaises(ValueError):
            inspect_local_resources(" ")

    def test_saves_valid_json_to_local_path(self):
        payload = {"state": "MEASURED_LOCAL_UNVERIFIED", "mining_started": False}
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "nested" / "measurement.json"
            saved = write_json_atomically(target, payload)
            self.assertEqual(saved, target)
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), payload)
            self.assertFalse(list(target.parent.glob("*.tmp")))


if __name__ == "__main__":
    unittest.main()
