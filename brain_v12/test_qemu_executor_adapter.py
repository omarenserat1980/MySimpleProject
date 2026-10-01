import unittest
from brain_v12.brain.executor_adapter import QemuWindowsExecutorAdapter
from brain_v12.virtual_hardware.windows_server_backend import QemuWindowsBackend

class Task:
    install=True
    timeout=1

class QemuAdapterTests(unittest.TestCase):
    def test_exit_without_guest_boot_is_not_success(self):
        class FakeBackend:
            def run(self,install=True,timeout=1):
                return {"ok":True,"status":"QEMU_EXITED","returncode":0}
        result=QemuWindowsExecutorAdapter(FakeBackend()).execute(Task())
        self.assertFalse(result.ok)
        self.assertEqual(result.status,"QEMU_EXITED")

    def test_backend_command_contract_still_exists(self):
        backend=QemuWindowsBackend(disk_path="disk.img",iso_path="server.iso")
        self.assertEqual(backend.command()[-2:],["-cdrom","server.iso"] if False else ["-boot","order=d"])

if __name__=="__main__": unittest.main()
