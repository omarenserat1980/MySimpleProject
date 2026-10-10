import unittest

from brain_v12.tools.brain_emulator_agent import execute
from brain_v12.brain.device_bridge import DeviceBridge


class SoftwareDiscoveryTests(unittest.TestCase):
    def test_inventory_is_read_only_and_scoped_to_python(self):
        result = execute("software_inventory")
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["scope"], "python-environment-only")
        self.assertIs(result["read_only"], True)
        self.assertIn("executable", result["python"])
        self.assertIn("package_count", result)
        self.assertLessEqual(len(result["packages"]), 300)
        if result["packages_truncated"]:
            self.assertGreater(result["package_count"], len(result["packages"]))
        else:
            self.assertEqual(result["package_count"], len(result["packages"]))

    def test_unknown_task_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "TASK_NOT_ALLOWED"):
            execute("run arbitrary command")

    def test_device_bridge_allows_only_named_inventory_task(self):
        self.assertIn("software_inventory", DeviceBridge.ALLOWED_TASKS)
        self.assertNotIn("shell", DeviceBridge.ALLOWED_TASKS)


if __name__ == "__main__":
    unittest.main()
