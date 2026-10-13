import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.arkan_software_node import ArkanSoftwareNode, NODE_ID


class TestArkanSoftwareNode(unittest.TestCase):
    def test_connect_uses_emulated_apps_only(self):
        with tempfile.TemporaryDirectory() as root:
            node = ArkanSoftwareNode(Path(root))
            state = node.connect()
            self.assertTrue(state["ok"])
            self.assertEqual(state["node_id"], NODE_ID)
            self.assertEqual(state["node_type"], "SOFTWARE_ONLY")
            self.assertFalse(state["physical_host_required"])
            self.assertFalse(state["native_desktop_commander_used"])
            self.assertFalse(state["native_powershell_used"])
            self.assertTrue(state["apps"]["desktop_commander"]["ready"])
            self.assertTrue(state["apps"]["powershell"]["ready"])
            self.assertEqual(state["reality"], "SIMULATED")
            self.assertFalse(state["execution_eligible"])

    def test_desktop_commander_emulator_filesystem_is_sandboxed(self):
        with tempfile.TemporaryDirectory() as root:
            node = ArkanSoftwareNode(root)
            node.connect()
            written = node.desktop_write("workspace/hello.txt", "Brain virtual Arkan")
            self.assertTrue(written["ok"])
            read = node.desktop_read("workspace/hello.txt")
            self.assertEqual(read["content"], "Brain virtual Arkan")
            escaped = node.desktop_read("../outside.txt")
            self.assertFalse(escaped["ok"])

    def test_powershell_emulator_runs_without_native_powershell(self):
        with tempfile.TemporaryDirectory() as root:
            node = ArkanSoftwareNode(root)
            node.connect()
            result = node.run_powershell("Write-Output hello; Get-ComputerInfo")
            self.assertTrue(result["ok"])
            self.assertIn("hello", result["output"])
            self.assertIn("BRAIN Virtual Windows", result["output"])
            self.assertEqual(result["execution_channel"], "BRAIN_POWERSHELL_EMULATOR")
            self.assertEqual(result["reality"], "SIMULATED")

    def test_unconnected_node_does_not_execute(self):
        with tempfile.TemporaryDirectory() as root:
            node = ArkanSoftwareNode(root)
            result = node.run_powershell("Write-Output should-not-run")
            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], "NODE_NOT_CONNECTED")

    def test_heartbeat_and_audit_never_claim_real_host(self):
        with tempfile.TemporaryDirectory() as root:
            node = ArkanSoftwareNode(root)
            node.connect()
            self.assertEqual(node.heartbeat()["node_id"], NODE_ID)
            audit = node.audit()
            self.assertFalse(audit["native_tools_invoked"])
            self.assertFalse(audit["physical_host_contacted"])
            self.assertEqual(audit["reality"], "SIMULATED")


if __name__ == "__main__":
    unittest.main()
