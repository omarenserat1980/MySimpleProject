import unittest
from unittest.mock import patch

from brain_v12.brain.habitat.api import android_open_app_test


class HabitatAndroidGateTests(unittest.TestCase):
    def test_android_open_app_uses_device_bridge_gate(self):
        class Request:
            headers = {}
        with patch("brain_v12.brain.habitat.api.require_control_key"), patch("brain_v12.brain.device_bridge.DeviceBridge.enqueue", return_value={"ok": True, "status": "QUEUED", "task": "brain-termux-test"} ) as enqueue:
            result = android_open_app_test(Request())
        self.assertEqual(result["status"], "QUEUED")
        enqueue.assert_called_once_with("open_app", {"package": "com.android.settings"})


if __name__ == "__main__":
    unittest.main()
