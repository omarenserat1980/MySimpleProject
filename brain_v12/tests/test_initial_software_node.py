from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.initial_software_node import InitialSoftwareNode, NODE_ID


class InitialSoftwareNodeTests(unittest.TestCase):
    def test_lifecycle_and_heartbeat_are_software_only(self):
        with tempfile.TemporaryDirectory() as root:
            node = InitialSoftwareNode(root)
            self.assertEqual(node.status()["state"], "STOPPED")
            self.assertFalse(node.heartbeat()["ok"])
            state = node.start()
            self.assertTrue(state["ok"])
            self.assertEqual(state["node_id"], NODE_ID)
            self.assertFalse(state["physical_host_contacted"])
            self.assertFalse(state["network_io_enabled"])
            self.assertFalse(state["shell_execution_enabled"])
            self.assertFalse(state["windows_server_2025_boot_verified"])
            self.assertTrue(node.heartbeat()["ok"])
            self.assertEqual(node.status()["heartbeat_count"], 1)
            self.assertEqual(node.stop()["state"], "STOPPED")

    def test_allowlisted_tasks_use_only_workspace(self):
        with tempfile.TemporaryDirectory() as root:
            node = InitialSoftwareNode(root)
            node.start()
            write = node.execute({"type": "write_text", "path": "jobs/result.txt", "content": "Brain node ready"})
            self.assertTrue(write["ok"])
            read = node.execute({"type": "read_text", "path": "jobs/result.txt"})
            self.assertEqual(read["result"]["content"], "Brain node ready")
            self.assertEqual(node.execute({"type": "health_check"})["result"]["health"], "OK")
            self.assertEqual(node.status()["completed_tasks"], 3)

    def test_rejects_shell_network_and_unknown_task_types(self):
        with tempfile.TemporaryDirectory() as root:
            node = InitialSoftwareNode(root)
            node.start()
            for kind in ("shell", "powershell", "http", "boot_windows", "unknown"):
                result = node.execute({"type": kind, "command": "whoami"})
                self.assertFalse(result["ok"])
                self.assertEqual(result["status"], "TASK_TYPE_NOT_ALLOWED")

    def test_rejects_path_traversal_and_symlink_escape(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as outside:
            node = InitialSoftwareNode(root)
            node.start()
            result = node.execute({"type": "write_text", "path": "../outside.txt", "content": "no"})
            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], "PATH_OUTSIDE_WORKSPACE")
            link = Path(root) / "escape"
            link.symlink_to(outside, target_is_directory=True)
            result = node.execute({"type": "write_text", "path": "escape/outside.txt", "content": "no"})
            self.assertFalse(result["ok"])
            self.assertFalse((Path(outside) / "outside.txt").exists())

    def test_stopped_node_refuses_tasks(self):
        with tempfile.TemporaryDirectory() as root:
            node = InitialSoftwareNode(root)
            result = node.execute({"type": "health_check"})
            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], "NODE_NOT_READY")


if __name__ == "__main__":
    unittest.main()
