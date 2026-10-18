import unittest
from unittest.mock import patch

from brain_v12.brain.software_resource_node import ResourcePlan, build_plan, qemu_command


class SoftwareResourceNodeTests(unittest.TestCase):
    @patch("brain_v12.brain.software_resource_node.shutil.which", return_value="/usr/bin/qemu-system-x86_64")
    @patch("brain_v12.brain.software_resource_node.kvm_available", return_value=False)
    @patch("brain_v12.brain.software_resource_node.host_memory_mib", return_value=8192)
    @patch("brain_v12.brain.software_resource_node.os.cpu_count", return_value=8)
    def test_plan_is_bounded_by_detected_host_resources(self, *_mocks):
        plan = build_plan(999, 999999)
        self.assertEqual(plan.host_cpu_count, 8)
        self.assertEqual(plan.host_memory_mib, 8192)
        self.assertEqual(plan.guest_cpu_count, 7)
        self.assertEqual(plan.guest_memory_mib, 4096)
        self.assertEqual(plan.accelerator, "tcg")
        self.assertEqual(plan.status, "PLAN_READY_NOT_EXECUTED")

    @patch("brain_v12.brain.software_resource_node.shutil.which", return_value="/usr/bin/qemu-system-x86_64")
    @patch("brain_v12.brain.software_resource_node.kvm_available", return_value=False)
    @patch("brain_v12.brain.software_resource_node.host_memory_mib", return_value=600)
    @patch("brain_v12.brain.software_resource_node.os.cpu_count", return_value=4)
    def test_low_host_memory_blocks_guest_allocation(self, *_mocks):
        plan = build_plan(2, 512)
        self.assertEqual(plan.host_memory_mib, 600)
        self.assertEqual(plan.guest_memory_mib, 0)
        self.assertEqual(plan.guest_cpu_count, 0)
        self.assertEqual(plan.status, "BLOCKED_INSUFFICIENT_OR_UNKNOWN_HOST_MEMORY")

    @patch("brain_v12.brain.software_resource_node.shutil.which", return_value="/usr/bin/qemu-system-x86_64")
    @patch("brain_v12.brain.software_resource_node.kvm_available", return_value=False)
    @patch("brain_v12.brain.software_resource_node.host_memory_mib", return_value=8192)
    @patch("brain_v12.brain.software_resource_node.os.cpu_count", return_value=1)
    def test_single_cpu_host_is_blocked(self, *_mocks):
        plan = build_plan(1, 512)
        self.assertEqual(plan.guest_cpu_count, 0)
        self.assertEqual(plan.status, "BLOCKED_INSUFFICIENT_HOST_CPU")

    def test_invalid_requests_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "REQUESTED_CPUS_MUST_BE_POSITIVE"):
            build_plan(0, 1024)
        with self.assertRaisesRegex(ValueError, "REQUESTED_MEMORY_MUST_BE_AT_LEAST_512_MIB"):
            build_plan(1, 128)

    def test_missing_qemu_is_blocked(self):
        with patch("brain_v12.brain.software_resource_node.shutil.which", return_value=None), \
             patch("brain_v12.brain.software_resource_node.kvm_available", return_value=False), \
             patch("brain_v12.brain.software_resource_node.host_memory_mib", return_value=8192), \
             patch("brain_v12.brain.software_resource_node.os.cpu_count", return_value=4):
            plan = build_plan(2, 1024)
        self.assertEqual(plan.status, "BLOCKED_MISSING_QEMU")
        self.assertEqual(plan.guest_memory_mib, 0)

    def test_command_contains_bounded_cpu_ram_and_tcg_fallback(self):
        plan = ResourcePlan(
            host_architecture="x86_64", host_cpu_count=8, host_memory_mib=8192,
            guest_cpu_count=2, guest_memory_mib=2048, accelerator="tcg",
            kvm_available=False, qemu="/usr/bin/qemu-system-x86_64",
            status="PLAN_READY_NOT_EXECUTED",
        )
        cmd = qemu_command(plan, "server.iso", "server.qcow2")
        self.assertIn("-smp", cmd)
        self.assertIn("2", cmd)
        self.assertIn("-m", cmd)
        self.assertIn("2048", cmd)
        self.assertIn("tcg,thread=multi", cmd)

    def test_blocked_plan_cannot_build_execution_command(self):
        plan = ResourcePlan(
            host_architecture="x86_64", host_cpu_count=1, host_memory_mib=512,
            guest_cpu_count=0, guest_memory_mib=0, accelerator="tcg",
            kvm_available=False, qemu="/usr/bin/qemu-system-x86_64",
            status="BLOCKED_INSUFFICIENT_HOST_CPU",
        )
        with self.assertRaisesRegex(RuntimeError, "BLOCKED_INSUFFICIENT_HOST_CPU"):
            qemu_command(plan, "server.iso", "server.qcow2")


if __name__ == "__main__":
    unittest.main()
