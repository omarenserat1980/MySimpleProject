import unittest
from unittest.mock import patch

from brain_v12.brain.habitat.api import android_project_test


class HabitatAndroidProjectTests(unittest.TestCase):
    def test_project_factory_routes_to_android_executor(self):
        class Request:
            headers = {}
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


if __name__ == "__main__":
    unittest.main()
