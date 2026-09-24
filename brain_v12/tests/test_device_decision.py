import unittest
from brain_v12.brain.decision_engine import DecisionEngine


class DeviceDecisionTests(unittest.TestCase):
    def test_device_goal_gets_safe_device_option(self):
        engine = DecisionEngine()
        options = engine.generate("اختبر اتصال Termux على جهاز Android")
        device = next(x for x in options if x["action"] == "device")
        self.assertEqual(device["tool_id"], "device.enqueue")
        self.assertEqual(device["risk"], "medium")
        self.assertIn("device_agent", device["requirements"])


if __name__ == "__main__":
    unittest.main()
