"""Regression tests for the Windows Server 2025 simulation-only policy."""
import unittest

from brain_v12.brain.execution_gateway import BrainExecutionGateway
from brain_v12.brain.windows_cloud_executor import WindowsCloudExecutor
from brain_v12.brain.windows_real_boot_qemu_adapter import WindowsRealBootQemuAdapter
from brain_v12.virtual_hardware.windows_server_backend import QemuWindowsBackend


class ProviderMustNotRun:
    name = "must-not-run"

    def provision_windows_server_2025(self, **kwargs):
        raise AssertionError("real provider must never be called")

    def status(self, vm_id):
        raise AssertionError("real provider must never be called")

    def destroy(self, vm_id):
        raise AssertionError("real provider must never be called")


class WindowsSimulationOnlyPolicyTests(unittest.TestCase):
    def test_execution_gateway_rejects_real_windows_capabilities(self):
        gateway = BrainExecutionGateway()
        for capability in (
            "windows-server-2025-real-boot",
            "windows-server-2025-cloud",
            "windows-server-2025-cloud-native",
            "windows-native-agent",
        ):
            with self.subTest(capability=capability):
                with self.assertRaisesRegex(
                    RuntimeError, "WINDOWS_REAL_EXECUTION_DISABLED_SIMULATION_ONLY"
                ):
                    gateway.authorize_task(capability, {})

    def test_qemu_adapter_refuses_real_boot_before_contract_access(self):
        with self.assertRaisesRegex(
            RuntimeError, "WINDOWS_REAL_EXECUTION_DISABLED_SIMULATION_ONLY"
        ):
            WindowsRealBootQemuAdapter().authorize("/path/that/must/not/be/read")

    def test_legacy_qemu_backend_returns_simulation_only_block(self):
        result = QemuWindowsBackend().run()
        self.assertFalse(result["ok"])
        self.assertEqual(
            result["status"], "WINDOWS_REAL_EXECUTION_DISABLED_SIMULATION_ONLY"
        )
        self.assertEqual(result["execution_mode"], "SIMULATION_ONLY")
        self.assertFalse(result["real_windows_boot_verified"])

    def test_cloud_executor_refuses_real_provisioning(self):
        executor = WindowsCloudExecutor(provider=ProviderMustNotRun())
        with self.assertRaisesRegex(
            RuntimeError, "WINDOWS_REAL_EXECUTION_DISABLED_SIMULATION_ONLY"
        ):
            executor.provision(name="must-not-be-created")


if __name__ == "__main__":
    unittest.main()
