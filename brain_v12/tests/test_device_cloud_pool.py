import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain_v12.brain.device_cloud_pool import DeviceCloudPool, local_host_node


class FakeBridge:
    def __init__(self, capacities):
        self._capacities = capacities

    def executor_capacities(self):
        return list(self._capacities)


class DeviceCloudPoolTests(unittest.TestCase):
    def test_local_host_is_measured_not_fabricated(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ, {"BRAIN_CLOUD_DISK_ROOT": tmp}, clear=False
        ):
            node = local_host_node(node_id="test-host")
        self.assertEqual(node.node_id, "test-host")
        self.assertTrue(node.observed)
        self.assertGreaterEqual(node.cpu_cores, 0)
        self.assertGreaterEqual(node.memory_mb, 0)
        self.assertGreaterEqual(node.disk_mb, 0)

    def test_android_capacity_joins_local_pool(self):
        bridge = FakeBridge([{
            "executor_id": "android-executor-redmi3-01",
            "capabilities": ["python.test"],
            "cpu_cores": 2,
            "memory_mb": 1500,
            "disk_mb": 3000,
            "online": True,
            "healthy": True,
            "metadata": {"platform": "android"},
        }])
        pool = DeviceCloudPool(bridge)
        self.assertEqual(pool.status()["status"], "REMOTE_NODE_OBSERVED")
        ids = {item.executor_id for item in pool.capacities()}
        self.assertIn("android-executor-redmi3-01", ids)

    def test_live_windows_executor_joins_pool_from_heartbeat_metadata(self):
        import time
        class FakeRecord:
            deleted = False
            value = {"metadata": {
                "platform": "windows", "cpu_cores": 8, "memory_mb": 3600,
                "disk_mb": 12000, "healthy": True,
                "capabilities": ["python.test", "code.build"],
            }}
        class FakeStore:
            def get(self, key):
                return FakeRecord() if key.endswith("windows-executor-arkan") else None
        class WindowsBridge(FakeBridge):
            store = type("S", (), {"device_agents": lambda self: [{
                "agent_id": "windows-executor-arkan", "last_seen": time.time()
            }]})()
            sync_adapter = type("A", (), {"store": FakeStore()})()
        pool = DeviceCloudPool(WindowsBridge([]))
        status = pool.status()
        arkan = next(n for n in status["nodes"] if n["node_id"] == "windows-executor-arkan")
        self.assertEqual(arkan["role"], "windows_executor")
        self.assertTrue(arkan["online"])
        self.assertEqual(arkan["cpu_cores"], 8)
        self.assertIn("windows-executor-arkan", {x.executor_id for x in pool.capacities()})

    def test_plan_is_zero_cost_and_fail_closed_for_missing_capability(self):
        pool = DeviceCloudPool(FakeBridge([]))
        decision = pool.plan(task_id="t1", capability="media.render")
        self.assertIn(decision.status, {"PLANNED", "BLOCKED_NO_EXECUTOR"})
        self.assertEqual(decision.estimated_cost_usd, 0.0)
        if decision.status == "BLOCKED_NO_EXECUTOR":
            self.assertTrue(decision.rejected)


if __name__ == "__main__":
    unittest.main()
