import unittest

from brain_v12.brain.cognitive_loop import CognitiveLoop


class MemoryStore:
    def __init__(self):
        self._state = {}
        self._memories = []
        self.events = []

    def state(self):
        return dict(self._state)

    def set_state(self, state):
        self._state = dict(state)

    def memories(self):
        return list(self._memories)

    def save_memory(self, key, value):
        self._memories.append({"key": key, "value": value})

    def event(self, event_type, payload=None):
        self.events.append({"type": event_type, "payload": payload or {}})


class CognitiveLoopEvidenceTests(unittest.TestCase):
    def test_cognitive_loop_completes_only_with_evidence(self):
        store = MemoryStore()
        loop = CognitiveLoop(store)

        result = loop.run("review current state safely")

        self.assertEqual(result["execution"]["status"], "COMPLETED")
        self.assertTrue(result["execution"]["evidence_ref"].startswith("cognitive://"))
        self.assertTrue(result["verification"]["result_verified"])
        self.assertTrue(result["verification"]["action_verified"])
        self.assertFalse(result["verification"]["goal_verified"])
        self.assertEqual(result["learning"]["status"], "RECORDED")
        self.assertFalse(result["learning"]["lesson"]["verified"])
        self.assertEqual(result["learning"]["lesson"]["outcome"], "ACTION_VERIFIED_NOT_GOAL")
        task = next(
            task for task in result["tasks"]["tasks"]
            if task["id"] == result["execution"]["task_id"]
        )
        self.assertEqual(task["status"], "COMPLETED")
        self.assertEqual(task["evidence_ref"], result["execution"]["evidence_ref"])

    def test_cognitive_loop_preserves_caller_provided_run_id(self):
        store = MemoryStore()
        loop = CognitiveLoop(store)

        result = loop.run("review current state safely", run_id="api-run-123")

        self.assertEqual(result["run_id"], "api-run-123")
        self.assertEqual(result["verification"]["run_id"], "api-run-123")
        self.assertEqual(store.state()["cognitive_trace"]["run_id"], "api-run-123")

    def test_cognitive_loop_does_not_complete_when_tool_fails(self):
        store = MemoryStore()
        loop = CognitiveLoop(store)
        loop.execute_tool = lambda *args, **kwargs: {
            "ok": False, "status": "UNAVAILABLE", "tool": "memory.read"
        }

        result = loop.run("review current state safely")

        self.assertEqual(result["execution"]["status"], "FAILED")
        self.assertFalse(result["verification"]["result_verified"])
        self.assertFalse(result["learning"]["lesson"]["verified"])
        task = next(
            task for task in result["tasks"]["tasks"]
            if task["id"] == result["execution"]["task_id"]
        )
        self.assertEqual(task["status"], "PENDING")


if __name__ == "__main__":
    unittest.main()
