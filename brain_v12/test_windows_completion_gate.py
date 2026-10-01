import unittest
from brain_v12.brain.windows_completion_gate import WindowsCompletionGate

class WindowsCompletionGateTests(unittest.TestCase):
    def test_refuses_qemu_exit(self):
        e={"media":1,"uefi":1,"cpu":1,"network":1,"storage":1,"qemu_status":"QEMU_EXITED",
           "guest":{"os":"Windows Server 2025","architecture":"x86_64","boot_verified":False}}
        r=WindowsCompletionGate().verify(e)
        self.assertFalse(r["verified"])
        self.assertIn("QEMU_EXIT_IS_NOT_BOOT_PROOF",r["reasons"])
    def test_accepts_complete_evidence(self):
        e={"media":1,"uefi":1,"cpu":1,"network":1,"storage":1,
           "guest":{"os":"Windows Server 2025","architecture":"x86_64","boot_verified":True}}
        self.assertEqual(WindowsCompletionGate().verify(e)["status"],"WINDOWS_BOOT_VERIFIED")

if __name__=="__main__": unittest.main()
