import unittest

from brain_v12.brain.capability_fabric import CapabilityFabric, ExecutorSpec
from brain_v12.tool_lifecycle import ToolState


class CapabilityFabricPromotionTests(unittest.TestCase):
    def test_verified_runner_is_registered_only_after_authorized_activation(self):
        fabric = CapabilityFabric()
        spec = ExecutorSpec("real-example", "example.run")
        runner = lambda selected: {"verified": True, "executor": selected.executor_id}

        result = fabric.promote_tool(
            spec=spec,
            simulate=lambda: True,
            build_real=lambda: runner,
            verify_real=lambda implementation: {
                "verified": True, "evidence_id": "adapter-probe-001"
            },
            activation_authorized=False,
        )
        self.assertEqual(result.state, ToolState.BLOCKED)
        self.assertEqual(fabric.discover("example.run"), [])
        with self.assertRaisesRegex(RuntimeError, "REAL_ADAPTER_NOT_ACTIVE"):
            fabric.run_registered(spec.executor_id, spec)

    def test_authorized_verified_runner_becomes_runnable(self):
        fabric = CapabilityFabric()
        spec = ExecutorSpec("real-example", "example.run")
        runner = lambda selected: {"executor": selected.executor_id, "outcome": "real-test"}

        result = fabric.promote_tool(
            spec=spec,
            simulate=lambda: True,
            build_real=lambda: runner,
            verify_real=lambda implementation: {
                "verified": True, "evidence_id": "adapter-probe-002"
            },
            activation_authorized=True,
        )
        self.assertEqual(result.state, ToolState.ACTIVE)
        self.assertEqual(fabric.run_registered(spec.executor_id, spec)["outcome"], "real-test")
        self.assertEqual(fabric.discover("example.run"), [spec])


if __name__ == "__main__":
    unittest.main()
