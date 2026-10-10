import unittest

from brain_v12.brain.apm_queue import APMQueue, QueueUnit


class APMQueueTests(unittest.TestCase):
    def test_priority_and_dependencies(self):
        q = APMQueue([
            QueueUnit("A", priority=20),
            QueueUnit("B", priority=10),
            QueueUnit("C", depends_on=("A",), priority=1),
        ])
        self.assertEqual([u.unit_id for u in q.ready()], ["B", "A"])
        q.claim("worker-1")
        q.complete("B")
        q.claim("worker-2")
        q.complete("A")
        self.assertEqual([u.unit_id for u in q.ready()], ["C"])

    def test_expired_unit_can_be_requeued(self):
        q = APMQueue([QueueUnit("A")])
        q.claim("worker-1")
        q.mark_expired("A")
        self.assertEqual(q.units["A"].state, "EXPIRED")
        q.requeue_expired("A")
        self.assertEqual(q.units["A"].state, "QUEUED")
        q.claim("worker-2")
        self.assertEqual(q.units["A"].attempt, 2)

    def test_missing_dependency_is_blocked(self):
        q = APMQueue([QueueUnit("A", depends_on=("MISSING",))])
        self.assertEqual([u.unit_id for u in q.ready()], [])
        self.assertEqual([u.unit_id for u in q.blocked()], ["A"])


if __name__ == "__main__":
    unittest.main()
