import unittest

from brain_v12.brain.android_executor_adapter import android_executor_capacities
from brain_v12.brain.portable_resource_orchestrator import (
    PortableResourceOrchestrator, ResourceDemand, ScheduleRequest,
)


class AndroidExecutorAdapterTests(unittest.TestCase):
    def setUp(self):
        self.agent = {
            "agent_id": "android-executor-redmi3-01",
            "last_seen": 995.0,
            "metadata": {
                "enrolled": True, "healthy": True,
                "capabilities": ["python.test", "shell", "media.render"],
                "permissions": ["python.test"],
                "cpu_cores": 2, "memory_mb": 1800, "disk_mb": 4000,
                "model": "Redmi", "android_version": "16",
            },
        }

    def test_enrolled_live_android_is_discovered_with_allowlisted_capabilities(self):
        found = android_executor_capacities([self.agent], now=1000, heartbeat_ttl_seconds=10)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].executor_id, "android-executor-redmi3-01")
        self.assertEqual(found[0].capabilities, frozenset({"python.test", "media.render"}))
        self.assertNotIn("shell", found[0].capabilities)
        self.assertFalse(found[0].is_local)

    def test_heartbeat_alone_does_not_enroll_device(self):
        agent = {**self.agent, "metadata": {"capabilities": ["python.test"],
                  "cpu_cores": 2, "memory_mb": 1800, "disk_mb": 4000}}
        self.assertEqual(android_executor_capacities([agent], now=1000), [])

    def test_stale_or_future_heartbeat_is_rejected(self):
        stale = {**self.agent, "last_seen": 900}
        future = {**self.agent, "last_seen": 1001}
        self.assertEqual(android_executor_capacities([stale, future], now=1000), [])

    def test_missing_or_invalid_capacity_is_rejected(self):
        agent = {**self.agent, "metadata": {**self.agent["metadata"], "memory_mb": 0}}
        self.assertEqual(android_executor_capacities([agent], now=1000), [])

    def test_adapter_candidate_can_be_selected_by_scheduler(self):
        found = android_executor_capacities([self.agent], now=1000)
        request = ScheduleRequest(
            task_id="android-test", capability="python.test",
            demand=ResourceDemand(cpu_cores=1, memory_mb=512, disk_mb=256),
            required_permissions=frozenset({"python.test"}),
        )
        decision = PortableResourceOrchestrator().plan(request, found)
        self.assertEqual(decision.status, "PLANNED")
        self.assertEqual(decision.executor_id, "android-executor-redmi3-01")

    def test_unhealthy_device_is_not_selected(self):
        agent = {**self.agent, "metadata": {**self.agent["metadata"], "healthy": False}}
        found = android_executor_capacities([agent], now=1000)
        request = ScheduleRequest(task_id="x", capability="python.test")
        decision = PortableResourceOrchestrator().plan(request, found)
        self.assertEqual(decision.status, "BLOCKED_NO_EXECUTOR")


if __name__ == "__main__":
    unittest.main()
