import unittest
from unittest.mock import patch

from fastapi import HTTPException

from brain_v12.brain.habitat.api import android_open_app_test, configure_device_bridge
from brain_v12.brain.device_bridge import DeviceBridge


class HabitatAndroidGateTests(unittest.TestCase):
    def tearDown(self):
        configure_device_bridge(None)

    def test_android_open_app_uses_shared_device_bridge_gate(self):
        class Request:
            headers = {}

        bridge = DeviceBridge(store=None)
        configure_device_bridge(bridge)
        with patch("brain_v12.brain.habitat.api.require_control_key"), patch(
            "brain_v12.brain.device_bridge.DeviceBridge.enqueue",
            return_value={"ok": True, "status": "QUEUED", "task": {"task_id": "brain-termux-test"}},
        ) as enqueue:
            result = android_open_app_test(Request())

        self.assertEqual(result["status"], "QUEUED")
        enqueue.assert_called_once_with("open_app", {"package": "com.android.settings"})

    def test_android_open_app_fails_closed_when_bridge_is_not_configured(self):
        class Request:
            headers = {}

        configure_device_bridge(None)
        with patch("brain_v12.brain.habitat.api.require_control_key"):
            with self.assertRaises(HTTPException) as raised:
                android_open_app_test(Request())

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(raised.exception.detail, "DEVICE_BRIDGE_NOT_CONFIGURED")


if __name__ == "__main__":
    unittest.main()
