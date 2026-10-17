import unittest
from unittest.mock import patch

from fastapi import HTTPException

from brain_v12.brain.habitat.api import android_project_test, configure_device_bridge
from brain_v12.brain.device_bridge import DeviceBridge


class HabitatAndroidProjectTests(unittest.TestCase):
    def tearDown(self):
        configure_device_bridge(None)

    def test_project_factory_routes_to_shared_android_executor(self):
        class Request:
            headers = {}

        configure_device_bridge(DeviceBridge(store=None))
        with patch("brain_v12.brain.habitat.api.require_control_key"), patch(
            "brain_v12.brain.device_bridge.DeviceBridge.enqueue",
            return_value={"ok": True, "status": "QUEUED"},
        ) as enqueue:
            result = android_project_test(Request(), "BrainHabitatTest")

        self.assertEqual(result["status"], "QUEUED")
        task, params = enqueue.call_args.args
        self.assertEqual(task, "create_app_project")
        self.assertEqual(params["name"], "BrainHabitatTest")
        self.assertIn("README.md", params["files"])
        self.assertIn("src/BrainHabitatTest.txt", params["files"])

    def test_project_creation_fails_closed_when_bridge_is_not_configured(self):
        class Request:
            headers = {}

        configure_device_bridge(None)
        with patch("brain_v12.brain.habitat.api.require_control_key"):
            with self.assertRaises(HTTPException) as raised:
                android_project_test(Request(), "BrainHabitatTest")

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(raised.exception.detail, "DEVICE_BRIDGE_NOT_CONFIGURED")


if __name__ == "__main__":
    unittest.main()
