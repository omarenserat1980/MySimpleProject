import unittest

from brain_v12.brain.capability_fabric import CapabilityFabric, ExecutorSpec


class CapabilityHealthIntegrationTests(unittest.TestCase):
    def test_unhealthy_executor_is_not_selected(self):
        fabric = CapabilityFabric()
        fabric.register(
            ExecutorSpec("bad", "media.render", priority=1),
            probe=lambda: {"available": False, "reason": "OFFLINE"},
        )
        fabric.register(
            ExecutorSpec("good", "media.render", priority=2),
            probe=lambda: {"available": True},
        )
        plan = fabric.plan("media.render", probe_before_select=True)
        self.assertEqual([x.executor_id for x in plan], ["good"])

    def test_health_failure_does_not_become_success(self):
        fabric = CapabilityFabric()
        fabric.register(
            ExecutorSpec("offline", "compute", priority=1),
            probe=lambda: False,
        )
        result = fabric.execute("compute", lambda _: "SHOULD_NOT_RUN")
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["executor_id"], None)

    def test_fallback_uses_healthy_executor(self):
        fabric = CapabilityFabric()
        fabric.register(
            ExecutorSpec("first", "code.execute", priority=1),
            probe=lambda: True,
        )
        fabric.register(
            ExecutorSpec("second", "code.execute", priority=2),
            probe=lambda: True,
        )
        result = fabric.execute(
            "code.execute",
            lambda spec: (_ for _ in ()).throw(RuntimeError("executor failure"))
            if spec.executor_id == "first" else "verified-result",
        )
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["executor_id"], "second")
        self.assertEqual(len(result["attempts"]), 2)


if __name__ == "__main__":
    unittest.main()
