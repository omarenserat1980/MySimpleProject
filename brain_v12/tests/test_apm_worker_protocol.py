import unittest

from brain_v12.brain.apm_worker_protocol import APMWorkerProtocol


class APMWorkerProtocolTests(unittest.TestCase):
    def test_claim_heartbeat_complete(self):
        p = APMWorkerProtocol(lease_seconds=10)
        lease = p.claim("chunk-1", "termux-01", now=100)
        self.assertEqual(lease.state, "CLAIMED")
        p.heartbeat(lease, now=105)
        self.assertEqual(lease.state, "RUNNING")
        p.complete(lease, "result.mp4", "evidence.json", now=106)
        self.assertTrue(p.reusable(lease))
        self.assertFalse(p.retryable(lease))

    def test_expired_lease_is_retryable(self):
        p = APMWorkerProtocol(lease_seconds=10)
        lease = p.claim("chunk-2", "github-01", now=100)
        p.expire_if_needed(lease, now=111)
        self.assertEqual(lease.state, "EXPIRED")
        self.assertTrue(p.retryable(lease))

    def test_expired_worker_cannot_complete(self):
        p = APMWorkerProtocol(lease_seconds=10)
        lease = p.claim("chunk-3", "redmi3-01", now=100)
        with self.assertRaises(RuntimeError):
            p.complete(lease, "result", "evidence", now=111)

    def test_completion_requires_evidence(self):
        p = APMWorkerProtocol()
        lease = p.claim("chunk-4", "worker-1", now=100)
        with self.assertRaises(ValueError):
            p.complete(lease, "result", "", now=101)


if __name__ == "__main__":
    unittest.main()
