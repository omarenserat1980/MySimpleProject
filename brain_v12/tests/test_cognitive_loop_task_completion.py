import tempfile
import unittest

from brain_v12.brain.cognitive_loop import CognitiveLoop
from brain_v12.brain.memory import MemoryStore


class CognitiveLoopTaskCompletionTests(unittest.TestCase):
    def make_loop(self):
        handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        handle.close()
        store = MemoryStore(handle.name)
        store.init()
        return CognitiveLoop(store)

    def test_tasks_complete_does_not_report_success_without_evidence(self):
        loop = self.make_loop()
        task = loop.tasks.create("evidence-gated completion")

        result = loop.execute_tool("tasks.complete", {"task_id": task["id"]})

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "EVIDENCE_REQUIRED")
        self.assertEqual(result["data"]["error"], "EVIDENCE_REQUIRED")
        self.assertEqual(loop.tasks.snapshot()["tasks"][0]["status"], "PENDING")

    def test_tasks_complete_reports_success_when_evidence_is_supplied(self):
        loop = self.make_loop()
        task = loop.tasks.create("verified completion")

        result = loop.execute_tool(
            "tasks.complete",
            {"task_id": task["id"], "evidence_ref": "test://verified"},
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["data"]["evidence_ref"], "test://verified")
        self.assertEqual(loop.tasks.snapshot()["tasks"][0]["status"], "COMPLETED")


if __name__ == "__main__":
    unittest.main()
