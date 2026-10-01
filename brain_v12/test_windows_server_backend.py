import unittest
from brain_v12.virtual_hardware.windows_server_backend import QemuWindowsBackend

class QemuWindowsBackendTests(unittest.TestCase):
    def test_command_contract(self):
        b=QemuWindowsBackend(disk_path="/brain/windows.raw",iso_path="/brain/WindowsServer2025.iso")
        cmd=b.command(True)
        self.assertEqual(cmd[0],"qemu-system-x86_64")
        self.assertIn("-cdrom",cmd)
        self.assertIn("/brain/WindowsServer2025.iso",cmd)

    def test_no_media_is_rejected(self):
        b=QemuWindowsBackend(disk_path="/brain/windows.raw")
        with self.assertRaises(ValueError): b.command(True)

if __name__=="__main__": unittest.main()
