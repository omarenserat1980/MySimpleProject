import unittest
from brain_v12.brain.windows_completion_gate import WindowsCompletionGate

def complete():
    return {
        "media":{"sha256":"a"*64},
        "uefi":{"ready":True},
        "cpu":{"x86_64":True},
        "network":{"adapter_up":True,"internet_443":True},
        "storage":{"filesystem":"NTFS","size_bytes":64*1024*1024*1024},
        "guest":{"os":"Windows Server 2025","architecture":"x86_64","boot_verified":True},
    }

class WindowsCompletionGateTests(unittest.TestCase):
    def test_refuses_qemu_exit(self):
        e=complete()
        e["qemu_status"]="QEMU_EXITED"
        e["guest"]["boot_verified"]=False
        r=WindowsCompletionGate().verify(e)
        self.assertFalse(r["verified"])
        self.assertIn("QEMU_EXIT_IS_NOT_BOOT_PROOF",r["reasons"])
    def test_accepts_complete_evidence(self):
        self.assertEqual(WindowsCompletionGate().verify(complete())["status"],"WINDOWS_BOOT_VERIFIED")
    def test_refuses_fake_network_storage(self):
        e=complete()
        e["network"]["adapter_up"]=False
        e["storage"]["size_bytes"]=1024
        r=WindowsCompletionGate().verify(e)
        self.assertFalse(r["verified"])
        self.assertIn("GUEST_NETWORK_NOT_VERIFIED",r["reasons"])
        self.assertIn("GUEST_STORAGE_TOO_SMALL",r["reasons"])

if __name__=="__main__": unittest.main()
