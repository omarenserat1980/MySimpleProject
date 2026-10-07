import json
import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.memory import MemoryStore


class TargetedDeviceTaskClaimTest(unittest.TestCase):
    def test_targeted_task_is_claimed_only_by_target_agent(self):
        with tempfile.TemporaryDirectory() as td:
            store = MemoryStore(Path(td) / "brain.db")
            store.init()
            store.device_task_create(
                "targeted-1", "open_app",
                {"package": "com.android.settings", "_target_agent_id": "android-executor-redmi3-01"},
                1.0,
            )
            self.assertIsNone(store.device_task_claim("redmi3-01"))
            task = store.device_task_claim("android-executor-redmi3-01")
            self.assertIsNotNone(task)
            self.assertEqual(task["task_id"], "targeted-1")
            self.assertEqual(task["agent_id"], "android-executor-redmi3-01")

    def test_untargeted_task_remains_available_to_any_agent(self):
        with tempfile.TemporaryDirectory() as td:
            store = MemoryStore(Path(td) / "brain.db")
            store.init()
            store.device_task_create("open-1", "python_version", {}, 1.0)
            task = store.device_task_claim("redmi3-01")
            self.assertEqual(task["task_id"], "open-1")


if __name__ == "__main__":
    unittest.main()
