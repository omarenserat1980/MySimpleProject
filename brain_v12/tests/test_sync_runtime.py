"""Tests for the offline-first synchronization runtime."""
from __future__ import annotations
import tempfile, unittest
from pathlib import Path
from brain_v12.brain.sync_engine import BrainSyncStore
from brain_v12.brain.sync_runtime import DurableSyncQueue, HeartbeatRegistry, reconcile

class TestSyncRuntime(unittest.TestCase):
    def test_queue_survives_restart_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"queue.jsonl"
            local=BrainSyncStore("phone")
            event=local.put("task/1",{"state":"RUNNING"},event_id="e1")
            q=DurableSyncQueue(path)
            self.assertTrue(q.enqueue(event))
            self.assertFalse(q.enqueue(event))
            q2=DurableSyncQueue(path)
            self.assertEqual(q2.counts()["PENDING"],1)
            remote=BrainSyncStore("cloud")
            evidence=reconcile(local,remote,q2)
            self.assertEqual(evidence["status"],"RECONCILED")
            self.assertEqual(remote.get("task/1").value,{"state":"RUNNING"})
            self.assertEqual(q2.counts()["ACKED"],1)

    def test_failure_is_retained_for_retry(self):
        with tempfile.TemporaryDirectory() as td:
            local=BrainSyncStore("phone")
            event=local.put("task/2",{"state":"PENDING"},event_id="e2")
            q=DurableSyncQueue(Path(td)/"q.jsonl"); q.enqueue(event)
            calls=[0]
            def sender(_):
                calls[0]+=1
                if calls[0]==1: raise RuntimeError("offline")
            self.assertEqual(q.replay(sender)["failed"],1)
            self.assertEqual(q.counts()["FAILED"],1)
            self.assertEqual(q.replay(sender)["acked"],1)

    def test_heartbeat_sequence_and_staleness(self):
        registry=HeartbeatRegistry(ttl_seconds=10)
        registry.touch("redmi3-01",timestamp=100.0)
        registry.touch("redmi3-01",timestamp=105.0)
        self.assertTrue(registry.is_online("redmi3-01",now=110.0))
        self.assertFalse(registry.is_online("redmi3-01",now=116.0))
        self.assertEqual(registry.status(now=116.0)[0]["sequence"],2)

    def test_reconcile_digest_and_audit_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            local=BrainSyncStore("phone"); remote=BrainSyncStore("cloud")
            event=local.put("memory/fact",{"value":"x"},event_id="e3")
            q=DurableSyncQueue(Path(td)/"q.jsonl"); q.enqueue(event)
            evidence=reconcile(local,remote,q)
            self.assertEqual(remote.snapshot()["digest"],evidence["remote_digest_after"])
            self.assertTrue(evidence["remote_audit_chain_valid"])
            self.assertEqual(len(evidence["evidence_digest"]),64)

if __name__=="__main__": unittest.main()
