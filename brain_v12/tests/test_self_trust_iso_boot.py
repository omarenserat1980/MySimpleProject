import unittest

from brain_v12.brain.self_trust_boot_gate import BootGateEvidence
from brain_v12.virtual_hardware.computer import VirtualComputer


class SelfTrustISOBootTests(unittest.TestCase):
    def test_verified_boot_reaches_brain_ready(self):
        c=VirtualComputer("brain-iso")
        evidence=BootGateEvidence(True,True,True,True,"task-verified")
        status=c.power_on(evidence)
        self.assertTrue(status["powered"])
        self.assertEqual(c.boot_record["boot_gate"]["status"],"BRAIN_READY")

    def test_unverified_boot_is_blocked_before_power_on(self):
        c=VirtualComputer("brain-iso")
        evidence=BootGateEvidence(True,True,True,False,"task-unverified")
        with self.assertRaisesRegex(RuntimeError,"BRAIN_BOOT_BLOCKED"):
            c.power_on(evidence)
        self.assertFalse(c.powered)
        self.assertEqual(c.boot_count,0)
        self.assertEqual(c.boot_record["status"],"BRAIN_BOOT_BLOCKED")

    def test_legacy_virtual_boot_still_works_without_gate(self):
        c=VirtualComputer("legacy-test")
        status=c.power_on()
        self.assertTrue(status["powered"])
        self.assertNotIn("boot_gate",c.boot_record)


if __name__ == "__main__":
    unittest.main()
