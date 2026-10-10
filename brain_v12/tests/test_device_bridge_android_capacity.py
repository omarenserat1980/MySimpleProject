import os
import tempfile
import time
import unittest
from pathlib import Path

from brain_v12.brain.device_bridge import DeviceBridge
from brain_v12.brain.memory import MemoryStore


class DeviceBridgeAndroidCapacityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = str(Path(self.temp.name) / "brain.db")
        self.store = MemoryStore(self.db)
        self.store.init()
        self.bridge = DeviceBridge(
            self.store,
            sync_adapter=__import__(
                "brain_v12.brain.device_sync_adapter", fromlist=["DeviceTaskSyncAdapter"]
            ).DeviceTaskSyncAdapter(Path(self.temp.name) / "sync.jsonl"),
        )

    def test_bridge_exposes_only_enrolled_android_capacities(self):
        agent_id = "android-executor-redmi3-01"
        now = time.time()
        self.store.device_agent_touch(agent_id, now)
        self.bridge.sync_adapter.heartbeat(agent_id, timestamp=now, metadata={
            "enrolled": True, "healthy": True, "capabilities": ["python.test"],
            "permissions": ["python.test"], "cpu_cores": 2,
            "memory_mb": 1500, "disk_mb": 3000,
        })
        candidates = self.bridge.executor_capacities()
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["executor_id"], agent_id)
        self.assertIn("python.test", candidates[0]["capabilities"])

    def test_heartbeat_without_enrollment_is_not_schedulable(self):
        agent_id = "android-executor-unenrolled"
        now = time.time()
        self.store.device_agent_touch(agent_id, now)
        self.bridge.sync_adapter.heartbeat(agent_id, timestamp=now, metadata={
            "capabilities": ["python.test"], "cpu_cores": 2,
            "memory_mb": 1500, "disk_mb": 3000,
        })
        self.assertEqual(self.bridge.executor_capacities(), [])


if __name__ == "__main__":
    unittest.main()
