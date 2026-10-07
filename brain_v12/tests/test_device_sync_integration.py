"""Integration tests for DeviceBridge -> DeviceTaskSyncAdapter offline-first flow."""
from __future__ import annotations
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain_v12.brain.device_bridge import DeviceBridge
from brain_v12.brain.sync_engine import BrainSyncStore
from brain_v12.brain.memory import MemoryStore
from brain_v12.brain.device_sync_adapter import DeviceTaskSyncAdapter


class TestDeviceSyncIntegration(unittest.TestCase):
    def test_queue_claim_complete_restart_replay_reconcile_digest(self):
        with tempfile.TemporaryDirectory() as td:
            queue_path = Path(td) / "device-sync.jsonl"
            device_store = MemoryStore(Path(td) / "device.db")
            device_store.init()
            adapter = DeviceTaskSyncAdapter(queue_path, replica_id="brain-device")
            bridge = DeviceBridge(device_store, sync_adapter=adapter)

            with patch.dict(
                os.environ,
                {"BRAIN_AGENT_KEY": "test-device-key", "BRAIN_ENABLE_DEVICE_BRIDGE": "1"},
                clear=False,
            ):
                queued = bridge.enqueue("python_version")
                self.assertTrue(queued["ok"])
                task_id = queued["task"]["task_id"]

                claimed = bridge.poll("redmi3-01")
                self.assertEqual(claimed["status"], "TASK_AVAILABLE")
                self.assertEqual(claimed["task"]["task_id"], task_id)

                reported = bridge.report(
                    task_id,
                    "redmi3-01",
                    True,
                    {"stdout": "Python 3.13.0", "returncode": 0, "evidence_ref": "ev-device-1"},
                )
                self.assertEqual(reported["status"], "COMPLETED")
                self.assertEqual(adapter.pending()[-1].value["evidence_ref"], "ev-device-1")

            recovered = DeviceTaskSyncAdapter(queue_path, replica_id="brain-device")
            self.assertGreaterEqual(len(recovered.pending()), 3)

            remote = BrainSyncStore("brain-cloud")
            evidence = recovered.reconcile(remote)
            self.assertEqual(evidence["status"], "RECONCILED")
            self.assertEqual(evidence["queue"]["failed"], 0)
            self.assertEqual(evidence["local_digest"], recovered.store.snapshot()["digest"])
            self.assertEqual(evidence["remote_digest_after"], remote.snapshot()["digest"])
            self.assertTrue(evidence["remote_audit_chain_valid"])
            self.assertEqual(len(evidence["evidence_digest"]), 64)
            self.assertEqual(recovered.queue.counts()["ACKED"], 3)

    def test_heartbeat_sequence_survives_adapter_runtime(self):
        with tempfile.TemporaryDirectory() as td:
            adapter = DeviceTaskSyncAdapter(Path(td) / "hb.jsonl", heartbeat_ttl=10)
            hb1, _ = adapter.heartbeat("redmi3-01", timestamp=100.0)
            hb2, _ = adapter.heartbeat("redmi3-01", timestamp=105.0)
            self.assertEqual((hb1.sequence, hb2.sequence), (1, 2))
            self.assertTrue(adapter.heartbeats.is_online("redmi3-01", now=110.0))
            self.assertFalse(adapter.heartbeats.is_online("redmi3-01", now=116.0))


if __name__ == "__main__":
    unittest.main()
