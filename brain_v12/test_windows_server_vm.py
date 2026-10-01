import os, tempfile, unittest, hashlib
from brain_v12.virtual_hardware.disk import VirtualDisk
from brain_v12.virtual_hardware.x86_64 import X86_64CPU
from brain_v12.virtual_hardware.uefi import VirtualUEFI
from brain_v12.virtual_hardware.os_image import OSImage
from brain_v12.virtual_hardware.windows_server import WindowsServerVM

class WindowsServerVMTests(unittest.TestCase):
    def test_sparse_disk(self):
        d=VirtualDisk(64*1024,4096)
        d.write(4094,b"brain")
        self.assertEqual(d.read(4094,5),b"brain")
        self.assertEqual(d.blocks.__len__(),2)

    def test_x86_64_subset(self):
        c=X86_64CPU()
        result=c.run([("MOVI","RAX",7),("MOVI","RBX",5),("ADD","RAX","RBX"),("OUT","RAX"),("HLT",)])
        self.assertEqual(result["output"],[12])
        self.assertTrue(result["halted"])

    def test_uefi(self):
        r=VirtualUEFI().boot(VirtualDisk(64*1024,4096))
        self.assertTrue(r["ok"])
        self.assertEqual(r["status"],"UEFI_READY")

    def test_windows_media_integrity_contract(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"WINDOWS-SERVER-2025-MEDIA-TEST")
            path=f.name
        try:
            digest=hashlib.sha256(open(path,"rb").read()).hexdigest()
            image=OSImage("Windows Server","2025","x86_64","ISO_OR_VHD",path,digest)
            self.assertTrue(image.inspect()["verified"])
        finally:
            os.unlink(path)

    def test_vm_refuses_fake_boot_without_real_media(self):
        vm=WindowsServerVM("blade-win-01")
        vm.attach_windows_server_2025(None)
        result=vm.boot()
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"],"OS_MEDIA_NOT_VERIFIED")

if __name__=="__main__":
    unittest.main()
