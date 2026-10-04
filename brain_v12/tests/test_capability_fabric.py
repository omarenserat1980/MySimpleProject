import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.capability_fabric import CapabilityFabric, ExecutorSpec
from brain_v12.brain.execution_verifier import ExecutionVerifier
from brain_v12.brain.autonomy_policy import AutonomyPolicy


class CapabilityFabricTests(unittest.TestCase):
    def test_fallback_requires_verified_artifact(self):
        fabric = CapabilityFabric(autonomy_policy=AutonomyPolicy(allow_paid=True))
        fabric.register(ExecutorSpec("local", "media.render", priority=10, cost_class="FREE"))
        fabric.register(ExecutorSpec("paid", "media.render", priority=30, cost_class="PAID", metadata={"tier": "PAID_EXTERNAL"}))
        calls = []

        with tempfile.TemporaryDirectory() as d:
            artifact = Path(d) / "output.mp4"
            artifact.write_bytes(b"real output")

            def runner(spec):
                calls.append(spec.executor_id)
                if spec.executor_id == "local":
                    raise RuntimeError("unavailable")
                return str(artifact)

            result = fabric.execute("media.render", runner, max_attempts=2)

        self.assertEqual(result["status"], "VERIFIED_COMPLETED")
        self.assertEqual(result["executor_id"], "paid")
        self.assertEqual(calls, ["local", "paid"])

    def test_brain_owned_executor_is_preferred_over_paid(self):
        fabric = CapabilityFabric(autonomy_policy=AutonomyPolicy(allow_paid=True))
        fabric.register(ExecutorSpec("paid", "ai.reasoning", priority=1, cost_class="PAID", metadata={"tier": "PAID_EXTERNAL"}))
        fabric.register(ExecutorSpec("brain", "ai.reasoning", priority=50, cost_class="FREE", metadata={"tier": "BRAIN_OWNED"}))
        self.assertEqual(fabric.plan("ai.reasoning")[0].executor_id, "brain")

    def test_paid_executor_is_blocked_by_default(self):
        fabric = CapabilityFabric()
        fabric.register(ExecutorSpec("paid", "ai.reasoning", priority=1, cost_class="PAID", metadata={"tier": "PAID_EXTERNAL"}))
        self.assertEqual(fabric.plan("ai.reasoning"), [])

    def test_permission_filter(self):
        fabric = CapabilityFabric()
        fabric.register(ExecutorSpec("safe", "publish", priority=10))
        fabric.register(ExecutorSpec(
            "oauth", "publish", priority=20,
            permissions=frozenset({"youtube.upload"})))
        self.assertEqual(
            [x.executor_id for x in fabric.plan("publish", {"youtube.upload"})],
            ["oauth"])

    def test_missing_capability_is_failure(self):
        result = CapabilityFabric().execute("missing", lambda _: True)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["attempts"], [])

    def test_unverified_media_output_is_rejected(self):
        fabric = CapabilityFabric()
        fabric.register(ExecutorSpec("local", "media.render"))
        result = fabric.execute("media.render", lambda _: "/missing/output.mp4")
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["attempts"][0]["error"], "POLICY_REJECTED")


if __name__ == "__main__":
    unittest.main()
