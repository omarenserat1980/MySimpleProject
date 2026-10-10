import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.apm_queue import APMQueue, QueueUnit
from brain_v12.brain.apm_queue_store import APMQueueStore


class APMQueueStoreTests(unittest.TestCase):
    def test_save_load_preserves_state(self):
        q = APMQueue([QueueUnit("A", priority=5), QueueUnit("B", depends_on=("A",))])
        q.claim("worker-1")
        with tempfile.TemporaryDirectory() as td:
            path = str(Path(td) / "queue.json")
            store = APMQueueStore()
            store.save(q, path)
            restored = store.load(path)
        self.assertEqual(restored.units["A"].state, "CLAIMED")
        self.assertEqual(restored.units["A"].worker_id, "worker-1")
        self.assertEqual(restored.units["B"].depends_on, ("A",))

    def test_recover_abandoned_claims(self):
        q = APMQueue([QueueUnit("A"), QueueUnit("B")])
        q.claim("worker-1")
        recovered = APMQueueStore().recover_workers(q)
        self.assertEqual(recovered, 1)
        self.assertEqual(q.units["A"].state, "QUEUED")
        self.assertIsNone(q.units["A"].worker_id)


if __name__ == "__main__":
    unittest.main()
