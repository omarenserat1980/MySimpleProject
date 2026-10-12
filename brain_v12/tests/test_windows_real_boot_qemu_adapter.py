import unittest
from pathlib import Path
from unittest.mock import patch
from brain_v12.brain.windows_real_boot_qemu_adapter import WindowsRealBootQemuAdapter

class FakeRunner:
    def require(self, capability):
        assert capability == "qemu"

class WindowsRealBootQemuAdapterTests(unittest.TestCase):
    def test_build_command_is_qemu_x86_64_and_uses_installed_disk(self):
        adapter=WindowsRealBootQemuAdapter(FakeRunner())
        with patch.object(Path,"exists",return_value=True):
            cmd=adapter.build_command(os_disk="os.qcow2",evidence_disk="evidence.img",
                                      proof_iso="proof.iso",ovmf_vars="OVMF_VARS.fd")
        joined=" ".join(cmd)
        self.assertEqual(cmd[0],"qemu-system-x86_64")
        self.assertIn("-machine",cmd)
        self.assertEqual(cmd[cmd.index("-machine")+1],"q35,accel=kvm")
        self.assertEqual(cmd[cmd.index("-m")+1],"2G")
        self.assertNotIn(" -machine",cmd)
        self.assertTrue(all(arg == arg.strip() for arg in cmd))
        self.assertNotIn("q35,accel=kvm:tcg",cmd)
        self.assertIn("file=os.qcow2,format=qcow2",joined)
        self.assertIn("if=none,id=osdisk",joined)
        self.assertIn("-nic",cmd)

    def test_start_cannot_bypass_contract_authorization(self):
        adapter=WindowsRealBootQemuAdapter(FakeRunner())
        with patch.object(adapter,"authorize",side_effect=RuntimeError("CONTRACT_REQUIRED")):
            with self.assertRaisesRegex(RuntimeError,"CONTRACT_REQUIRED"):
                adapter.start(os_disk="os.qcow2",evidence_disk="evidence.img",
                              proof_iso="proof.iso",ovmf_vars="OVMF_VARS.fd")

if __name__=="__main__":
    unittest.main()
