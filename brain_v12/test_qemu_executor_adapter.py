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

    def test_real_backend_command_is_disabled(self):
        backend=QemuWindowsBackend(disk_path="disk.img",iso_path="server.iso")
        with self.assertRaisesRegex(
            RuntimeError, "WINDOWS_REAL_EXECUTION_DISABLED_SIMULATION_ONLY"
        ):
            backend.command()

if __name__=="__main__": unittest.main()
