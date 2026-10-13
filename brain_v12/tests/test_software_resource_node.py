import os
import unittest
from brain_v12.brain.software_resource_node import build_plan, qemu_command


class SoftwareResourceNodeTests(unittest.TestCase):
    def test_plan_is_backed_by_host_resources(self):
        plan = build_plan(999, 999999)
        self.assertGreaterEqual(plan.host_cpu_count, 1)
        self.assertGreaterEqual(plan.host_memory_mib, 512)
        self.assertGreaterEqual(plan.guest_cpu_count, 1)
        self.assertGreaterEqual(plan.guest_memory_mib, 512)
        self.assertIn(plan.accelerator, {"kvm", "tcg"})

    def test_tcg_fallback_does_not_claim_kvm(self):
        plan = build_plan(1, 512)
        if not plan.kvm_available:
            self.assertEqual(plan.accelerator, "tcg")
        self.assertIn(plan.accelerator, {"kvm", "tcg"})

    def test_command_contains_real_virtual_cpu_and_ram(self):
        plan = build_plan(1, 512)
        if plan.status != "READY":
            self.skipTest("QEMU unavailable on test host")
        cmd = qemu_command(plan, "server.iso", "server.qcow2")
        self.assertIn("-smp", cmd)
        self.assertIn(str(plan.guest_cpu_count), cmd)
        self.assertIn("-m", cmd)
        self.assertIn(str(plan.guest_memory_mib), cmd)
        self.assertIn("-accel", cmd)
        self.assertIn("kvm" if plan.kvm_available else "tcg", " ".join(cmd))


if __name__ == "__main__":
    unittest.main()
