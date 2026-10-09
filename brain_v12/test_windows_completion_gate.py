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
        "boot_source":"windows-installed-disk",
        "executor":{"verified":True,"executor_id":"executor-test","hostname":"runner-test","evidence_ref":"cloud-executor-gate:test","runner_name":"runner-test","workflow_run_id":"123"},
        "control": {"schema":"brain.windows-execution-contract.v1","status":"VERIFIED","capability":"windows-server-2025-real-boot","executor":"windows-real-boot-qemu","brain_id":"brain-test","generation":1,"fencing_token":1,"task_id":"t1","attempt_id":"a1"},
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
    def test_refuses_missing_executor_binding(self):
        e=complete()
        e.pop("executor")
        r=WindowsCompletionGate().verify(e)
        self.assertFalse(r["verified"])
        self.assertIn("MISSING_EXECUTOR",r["reasons"])

    def test_refuses_missing_control(self):
        e=complete()
        e.pop("control")
        r=WindowsCompletionGate().verify(e)
        self.assertFalse(r["verified"])
        self.assertIn("MISSING_CONTROL",r["reasons"])

    def test_refuses_iso_boot(self):
        e=complete()
        e["boot_source"]="iso"
        r=WindowsCompletionGate().verify(e)
        self.assertFalse(r["verified"])
        self.assertIn("BOOT_SOURCE_NOT_INSTALLED_DISK",r["reasons"])
    def test_refuses_fake_network_storage(self):
        e=complete()
        e["network"]["adapter_up"]=False
        e["storage"]["size_bytes"]=1024
        r=WindowsCompletionGate().verify(e)
        self.assertFalse(r["verified"])
        self.assertIn("GUEST_NETWORK_NOT_VERIFIED",r["reasons"])
        self.assertIn("GUEST_STORAGE_TOO_SMALL",r["reasons"])

if __name__=="__main__": unittest.main()
