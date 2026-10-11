import tempfile,unittest
from pathlib import Path
from brain_v12.brain.desktop_commander_emulator import DesktopCommanderEmulator,EmulatorPolicy

class EmulatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.e=DesktopCommanderEmulator(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def test_sandbox_escape_is_denied(self):
        with self.assertRaises(PermissionError): self.e.read_file("../outside")
    def test_filesystem_roundtrip(self):
        self.assertTrue(self.e.write_file("Downloads/a.txt","hello")["ok"])
        self.assertEqual(self.e.read_file("Downloads/a.txt")["content"],"hello")
        self.assertEqual(self.e.list_dir("Downloads")["items"][0]["name"],"a.txt")
    def test_audit_and_heartbeat(self):
        self.e.heartbeat({"source":"test"})
        self.assertEqual(self.e.audit()["records"][-1]["action"],"heartbeat")
    def test_shell_fail_closed(self):
        self.assertEqual(self.e.start_process("python --version")["status"],"SHELL_DISABLED")

    def test_info_marks_virtual_reality(self):
        info=self.e.info()
        self.assertEqual(info["reality"],"SIMULATED")
        self.assertEqual(info["execution_scope"],"LOCAL_SANDBOX_ONLY")

    def test_invalid_environment_is_rejected(self):
        e=DesktopCommanderEmulator(self.tmp.name,policy=EmulatorPolicy(Path(self.tmp.name),allow_shell=True))
        result=e.start_process("python --version",env={"BROKEN":None})
        self.assertEqual(result["status"],"INVALID_ENVIRONMENT")

    def test_process_timeout_is_enforced(self):
        import sys
        e=DesktopCommanderEmulator(
            self.tmp.name,
            policy=EmulatorPolicy(Path(self.tmp.name),allow_shell=True,command_timeout_seconds=0.05),
        )
        result=e.start_process(f'"{sys.executable}" -c "import time; time.sleep(2)"')
        self.assertTrue(result["ok"])
        output=e.read_process_output(result["process_id"],timeout=0.2)
        self.assertEqual(output["status"],"TIMED_OUT")
        self.assertEqual(e.process_snapshot()["processes"],[])
    def test_process_roundtrip_when_explicitly_enabled(self):
        e=DesktopCommanderEmulator(self.tmp.name,policy=EmulatorPolicy(Path(self.tmp.name),allow_shell=True))
        r=e.start_process("python --version")
        self.assertTrue(r["ok"])
        out=e.read_process_output(r["process_id"],2)
        self.assertEqual(out["returncode"],0); self.assertIn("Python",out["output"])
if __name__=="__main__": unittest.main()
