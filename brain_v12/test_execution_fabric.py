import tempfile
import unittest

from brain_v12.brain.execution_fabric import ExecutionFabric
from brain_v12.brain.internal_task_runtime import InternalTaskRuntime


class FabricTests(unittest.TestCase):
    def test_capability_routing_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            fabric = ExecutionFabric(InternalTaskRuntime(d))
            with self.assertRaisesRegex(RuntimeError, "NO_BRAIN_WORKER_FOR"):
                fabric.resolve("gpu")

    def test_local_worker_can_execute(self):
        with tempfile.TemporaryDirectory() as d:
            runtime = InternalTaskRuntime(d)
            fabric = ExecutionFabric(runtime)

            def execute(argv, capability, timeout):
                return {"ok": True, "stdout": "done", "capability": capability}

            fabric.register("local-01", "local", {"brain-internal-execution"}, execute)
            result = fabric.execute(
                "task-1", ["echo", "ok"], "brain-internal-execution"
            )
            self.assertTrue(result["ok"])
            self.assertEqual(result["worker_id"], "local-01")
            self.assertEqual(fabric.recover()["active_leases"], [])

    def test_offline_worker_is_not_selected(self):
        with tempfile.TemporaryDirectory() as d:
            fabric = ExecutionFabric(InternalTaskRuntime(d))
            fabric.register("local-01", "local", {"media"}, lambda *a: {"ok": True})
            fabric.heartbeat("local-01", online=False)
            with self.assertRaisesRegex(RuntimeError, "NO_BRAIN_WORKER_FOR"):
                fabric.resolve("media")


if __name__ == "__main__":
    unittest.main()
