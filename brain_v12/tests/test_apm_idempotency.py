import unittest

from brain_v12.brain.apm_idempotency import APMIdempotencyGuard, IdempotencyKey


class APMIdempotencyTests(unittest.TestCase):
    def test_same_input_gets_same_key(self):
        a = IdempotencyKey.create("A", "fp1")
        b = IdempotencyKey.create("A", "fp1")
        self.assertEqual(a.key, b.key)

    def test_second_worker_cannot_duplicate_active_unit(self):
        guard = APMIdempotencyGuard()
        key = IdempotencyKey.create("A", "fp1")
        self.assertTrue(guard.acquire(key, "worker-1"))
        self.assertFalse(guard.acquire(key, "worker-2"))
        self.assertEqual(guard.acquire(key, "worker-1"), True)

    def test_completed_result_is_reused(self):
        guard = APMIdempotencyGuard()
        key = IdempotencyKey.create("A", "fp1")
        guard.acquire(key, "worker-1")
        guard.complete(key, "artifact:A")
        self.assertEqual(guard.result(key), "artifact:A")
        self.assertFalse(guard.acquire(key, "worker-2"))


if __name__ == "__main__":
    unittest.main()
