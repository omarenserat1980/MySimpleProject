from __future__ import annotations

import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from brain_v12.brain.software_node_agent import SoftwareNodeAgent


class SoftwareNodeAgentHeartbeatTests(unittest.TestCase):
    def test_started_agent_persists_repeated_simulated_heartbeats(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            agent = SoftwareNodeAgent(
                root / "workspace",
                database_path=root / "state.sqlite3",
                heartbeat_interval=0.02,
                poll_interval=0.02,
            )
            try:
                started = agent.start()
                first_sequence = started["heartbeat"]["sequence"]
                self.assertEqual(started["agent_state"], "RUNNING_SIMULATED")
                self.assertTrue(started["task_worker_alive"])
                self.assertEqual(started["heartbeat"]["state"], "READY_SIMULATED")

                deadline = time.monotonic() + 2.0
                latest = agent.status()
                while latest["heartbeat"]["sequence"] <= first_sequence and time.monotonic() < deadline:
                    time.sleep(0.01)
                    latest = agent.status()

                self.assertGreater(latest["heartbeat"]["sequence"], first_sequence)
                self.assertIsNotNone(latest["heartbeat"]["timestamp"])
                self.assertTrue(latest["task_worker_alive"])
                self.assertFalse(latest["physical_host_contacted"])
                self.assertFalse(latest["network_io_enabled"])
            finally:
                stopped = agent.stop()

            self.assertEqual(stopped["agent_state"], "STOPPED")
            self.assertEqual(stopped["heartbeat"]["state"], "STOPPED")
            self.assertFalse(stopped["task_worker_alive"])
            self.assertFalse(stopped["windows_server_2025_boot_verified"])


if __name__ == "__main__":
    unittest.main()
