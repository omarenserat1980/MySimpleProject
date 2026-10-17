import unittest

from brain_v12.brain.apm_dispatcher import APMDispatcher
from brain_v12.brain.apm_queue import APMQueue, QueueUnit
from brain_v12.brain.apm_worker_protocol import APMWorkerProtocol


class APMDispatcherTests(unittest.TestCase):
    def test_dispatch_heartbeat_complete(self):
        q = APMQueue([QueueUnit("A")])
        d = APMDispatcher(q, APMWorkerProtocol(lease_seconds=10))
        item = d.dispatch("worker-1")
        self.assertIsNotNone(item)
        d.heartbeat("A", now=105)
        lease = d.complete("A", "artifact:A", "evidence:A", now=106)
        self.assertEqual(lease.state, "VERIFIED_COMPLETED")
        self.assertTrue(q.all_verified())

    def test_expired_work_is_requeued(self):
        q = APMQueue([QueueUnit("A")])
        d = APMDispatcher(q, APMWorkerProtocol(lease_seconds=10))
        d.dispatch("worker-1")
        self.assertTrue(d.recover_expired("A", now=111))
        self.assertEqual(q.units["A"].state, "QUEUED")
        self.assertEqual(d.pending(), 1)


if __name__ == "__main__":
    unittest.main()
