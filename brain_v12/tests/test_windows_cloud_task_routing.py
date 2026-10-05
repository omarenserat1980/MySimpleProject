import unittest

from brain_v12.brain.execution_gateway import BrainExecutionGateway
from brain_v12.brain.internal_task_runtime import InternalTaskRuntime


class WindowsCloudTaskRoutingTests(unittest.TestCase):
    def setUp(self):
        self.gateway = BrainExecutionGateway()
        self.vm = {
            "vm_id": "win-cloud-01",
            "provider": "azure",
            "region": "westeurope",
            "state": "RUNNING",
            "os": "Windows Server 2025",
            "architecture": "x86_64",
        }
        self.node = {
            "node_id": "win-cloud-01",
            "provider": "azure",
            "state": "READY",
            "architecture": "x86_64",
            "last_heartbeat": 990.0,
            "capabilities": [
                "windows-server-2025",
                "windows-cloud",
                "brain-heartbeat",
            ],
        }

    def test_windows_task_requires_explicit_cloud_executor(self):
        with self.assertRaisesRegex(
            RuntimeError, "WINDOWS_REAL_BOOT_REQUIRES_EXPLICIT_WINDOWS_CLOUD"
        ):
            self.gateway.authorize_task(
                "windows-server-2025-real-boot",
                {"executor": "brain-internal"},
            )

    def test_windows_task_requires_runtime_evidence(self):
        with self.assertRaisesRegex(
            RuntimeError, "WINDOWS_CLOUD_RUNTIME_EVIDENCE_REQUIRED"
        ):
            self.gateway.authorize_task(
                "windows-server-2025-real-boot",
                {"executor": "windows-server-2025-cloud"},
            )

    def test_stale_cloud_runtime_is_blocked_by_task_authorization(self):
        node = dict(self.node)
        node["last_heartbeat"] = 800.0
        with self.assertRaisesRegex(RuntimeError, "WINDOWS_CLOUD_HEARTBEAT_STALE"):
            self.gateway.authorize_task(
                "windows-server-2025-real-boot",
                {
                    "executor": "windows-server-2025-cloud",
                    "vm": self.vm,
                    "node": node,
                    "heartbeat_timeout": 120.0,
                    "now": 1000.0,
                },
            )

    def test_local_runtime_never_executes_windows_task(self):
        runtime = InternalTaskRuntime(
            root=".brain/test-windows-cloud-routing",
            gateway=self.gateway,
        )
        runtime.enqueue(
            "windows-task",
            ["echo", "must-not-run-locally"],
            capability="windows-server-2025-real-boot",
            metadata={
                "executor": "windows-server-2025-cloud",
                "vm": self.vm,
                "node": self.node,
                "heartbeat_timeout": 120.0,
                "now": 1000.0,
            },
        )
        result = runtime.run_one()
        self.assertEqual(result["state"], "BLOCKED")
        self.assertIn("WINDOWS_CLOUD_EXECUTION_ADAPTER_REQUIRED", result["error"])


if __name__ == "__main__":
    unittest.main()
