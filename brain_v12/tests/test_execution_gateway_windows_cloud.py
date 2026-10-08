import unittest

from brain_v12.brain.execution_gateway import BrainExecutionGateway
from brain_v12.brain.execution_policy import WINDOWS_CLOUD_NATIVE
from brain_v12.brain.windows_cloud_executor import CloudWindowsVM


class WindowsCloudExecutionGatewayTests(unittest.TestCase):
    def setUp(self):
        self.gateway = BrainExecutionGateway()
        self.vm = CloudWindowsVM(
            vm_id="win-cloud-01",
            provider="azure",
            region="westeurope",
            state="RUNNING",
        )

    def node(self, heartbeat):
        return {
            "node_id": "win-cloud-01",
            "provider": "azure",
            "state": "READY",
            "architecture": "x86_64",
            "last_heartbeat": heartbeat,
            "capabilities": [
                "windows-server-2025",
                "windows-cloud",
                "brain-heartbeat",
            ],
        }

    def test_real_boot_wrong_executor_is_rejected_by_router(self):
        with self.assertRaisesRegex(
            RuntimeError, "NO_WINDOWS_ROUTE_FOR|WINDOWS_REAL_BOOT_REQUIRES_QEMU_CLOUD"
        ):
            self.gateway.authorize_task(
                "windows-server-2025-real-boot",
                {"executor": "windows-server-2025-cloud"},
            )

    def test_real_boot_qemu_reaches_runtime_adapter_gate(self):
        with self.assertRaisesRegex(
            RuntimeError, "WINDOWS_REAL_BOOT_QEMU_RUNTIME_ADAPTER_NOT_CONFIGURED"
        ):
            self.gateway.authorize_task(
                "windows-server-2025-real-boot",
                {"executor": "windows-real-boot-qemu"},
            )

    def test_fresh_guest_heartbeat_authorizes_windows_cloud(self):
        decision = self.gateway.authorize_windows_cloud(
            self.vm,
            self.node(990.0),
            heartbeat_timeout=120.0,
            now=1000.0,
        )
        self.assertEqual(decision.executor, "windows-server-2025-cloud")
        self.assertEqual(decision.capability, WINDOWS_CLOUD_NATIVE)
        self.assertTrue(decision.verified)
        self.assertEqual(decision.reason, "WINDOWS_CLOUD_NATIVE_RUNTIME_VERIFIED")

    def test_stale_guest_heartbeat_is_blocked(self):
        with self.assertRaisesRegex(
            RuntimeError, "WINDOWS_CLOUD_HEARTBEAT_STALE"
        ):
            self.gateway.authorize_windows_cloud(
                self.vm,
                self.node(800.0),
                heartbeat_timeout=120.0,
                now=1000.0,
            )

    def test_wrong_node_is_blocked(self):
        node = self.node(990.0)
        node["node_id"] = "different-node"
        with self.assertRaisesRegex(
            RuntimeError, "WINDOWS_CLOUD_VM_ID_MISMATCH"
        ):
            self.gateway.authorize_windows_cloud(
                self.vm,
                node,
                heartbeat_timeout=120.0,
                now=1000.0,
            )


if __name__ == "__main__":
    unittest.main()
