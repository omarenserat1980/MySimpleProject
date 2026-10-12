import tempfile, unittest
from pathlib import Path
from brain_v12.brain.sync_engine import BrainSyncStore
from brain_v12.brain.sync_runtime import DurableSyncQueue
from brain_v12.brain.task_sync_adapter import TaskSyncAdapter

class TestTaskSyncAdapter(unittest.TestCase):
    def test_task_transition_and_evidence_survive_offline_reconnect(self):
        with tempfile.TemporaryDirectory() as td:
            phone=BrainSyncStore("redmi3-01")
            cloud=BrainSyncStore("brain-cloud")
            queue=DurableSyncQueue(Path(td)/"sync.jsonl")
            adapter=TaskSyncAdapter(phone,queue)
            result=adapter.publish_transition(
                {"id":"t-100","title":"verified work","status":"COMPLETED","attempts":1},
                evidence={"stage":"verification","status":"VERIFIED","evidence_ref":"ev-100"},
            )
            self.assertEqual(queue.counts()["PENDING"],2)
            remote=queue.replay(lambda e: cloud.apply([e]))
            self.assertEqual(remote["acked"],2)
            self.assertEqual(cloud.get("task/t-100").value["status"],"COMPLETED")
            self.assertEqual(cloud.get("evidence/t-100").value["evidence_ref"],"ev-100")
            self.assertTrue(cloud.audit_chain_valid())
            self.assertEqual(result["task_event_id"] != result["evidence_event_id"],True)

    def test_conflict_is_explicit(self):
        with tempfile.TemporaryDirectory() as td:
            store=BrainSyncStore("phone"); queue=DurableSyncQueue(Path(td)/"q.jsonl")
            adapter=TaskSyncAdapter(store,queue)
            adapter.publish_task({"id":"t-1","status":"PENDING"},event_id="e1")
            outcome=adapter.conflict_safe_update("task/t-1",{"id":"t-1","status":"RUNNING"},expected_revision=0,event_id="e2")
            self.assertEqual(outcome["status"],"CONFLICT")
            self.assertEqual(queue.counts()["PENDING"],1)

if __name__=="__main__": unittest.main()
