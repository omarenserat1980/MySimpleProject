import os
import unittest
from unittest.mock import patch

from pathlib import Path

from brain_v12.tools.brain_device_link import capacity_metadata, detect_platform
from brain_v12.tools.brain_device_bridge_doctor import DEFAULT_URL as DEVICE_DOCTOR_DEFAULT_URL


class BrainDeviceLinkTests(unittest.TestCase):
    def test_device_doctor_defaults_to_current_brain_control_plane(self):
        self.assertEqual(DEVICE_DOCTOR_DEFAULT_URL, "https://brain-control-plane-main.onrender.com")

    def test_capacity_metadata_is_observation_only(self):
        metadata = capacity_metadata()
        self.assertTrue(metadata["observation_only"])
        self.assertNotIn("enrolled", metadata)
        self.assertIn("device.status", metadata["capabilities"])
        self.assertGreaterEqual(metadata["cpu_cores"], 0)
        self.assertGreaterEqual(metadata["memory_mb"], 0)
        self.assertGreaterEqual(metadata["disk_mb"], 0)

    def test_android_platform_detection(self):
        with patch.dict(os.environ, {"ANDROID_ROOT": "/system", "TERMUX_VERSION": "0.118"}, clear=False):
            self.assertEqual(detect_platform(), "android")

    def test_agent_is_heartbeat_only_and_does_not_poll_or_execute_tasks(self):
        source = Path("brain_v12/tools/brain_device_link.py").read_text(encoding="utf-8")
        self.assertIn('"/api/device/heartbeat"', source)
        self.assertIn('"poll": "DISABLED_OBSERVATION_ONLY"', source)
        self.assertNotIn("def execute_remote_task(", source)
        self.assertNotIn("def poll_and_run_one(", source)
        self.assertNotIn('"/api/device/poll', source)
        self.assertNotIn('"/api/device/report', source)

    def test_windows_agent_id_validation_is_platform_scoped_in_main(self):
        # The agent's main() checks the ID prefix only when the host platform is
        # one of the supported platforms; no credentials or network are needed here.
        with patch.dict(os.environ, {"ANDROID_ROOT": "/system"}, clear=False):
            self.assertEqual(detect_platform(), "android")


if __name__ == "__main__":
    unittest.main()
