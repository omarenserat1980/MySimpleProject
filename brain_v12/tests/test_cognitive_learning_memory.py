import json
import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.cognitive_loop import CognitiveLoop
from brain_v12.brain.memory import MemoryStore


class CognitiveLearningMemoryTests(unittest.TestCase):
    def test_each_run_keeps_a_separate_structured_learning_record(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(str(Path(directory) / "brain.db"))
            store.init()
            loop = CognitiveLoop(store)

            first = loop.run("observe status")
            second = loop.run("observe status")

            memories = {item["key"]: item["value"] for item in store.memories()}
            first_key = f"cognitive.run.{first['run_id']}"
            second_key = f"cognitive.run.{second['run_id']}"

            self.assertIn(first_key, memories)
            self.assertIn(second_key, memories)
            self.assertNotEqual(first_key, second_key)

            first_lesson = json.loads(memories[first_key])
            second_lesson = json.loads(memories[second_key])
            self.assertEqual(first_lesson["run_id"], first["run_id"])
            self.assertEqual(second_lesson["run_id"], second["run_id"])
            self.assertIn(first_lesson["outcome"], {
                "VERIFIED_SUCCESS", "WAITING_PERMISSION", "FAILED_OR_UNVERIFIED"
            })
            self.assertIn("verified", second_lesson)
            self.assertGreaterEqual(second["prior_lesson_count"], 1)
            self.assertFalse(second["decision"]["selected"]["learned_memory_support"])
            self.assertEqual(first_lesson["outcome"], "ACTION_VERIFIED_NOT_GOAL")


    def test_only_explicitly_verified_goal_success_can_influence_future_choice(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(str(Path(directory) / "brain.db"))
            store.init()
            verifier = lambda goal, execution, tool_result: {
                "verified": True,
                "evidence": "test verifier confirmed the requested goal",
                "verifier": "unit-test-goal-verifier",
            }
            loop = CognitiveLoop(store, goal_verifier=verifier)

            first = loop.run("observe status")
            second = loop.run("observe status")

            self.assertTrue(first["verification"]["goal_verified"])
            self.assertTrue(first["learning"]["lesson"]["verified"])
            self.assertEqual(first["learning"]["lesson"]["outcome"], "VERIFIED_SUCCESS")
            self.assertTrue(second["decision"]["selected"]["learned_memory_support"])



    def test_blocked_medium_risk_option_is_not_reported_as_decided(self):
        from brain_v12.brain.decision_engine import DecisionEngine

        options = [
            {"id":"device","action":"query device","risk":"medium","requirements":["device_agent"],
             "reversible":True,"confidence":0.99},
            {"id":"observe","action":"read state","risk":"low","requirements":[],
             "reversible":True,"confidence":0.70},
        ]
        result = DecisionEngine().choose("check device", options, permissions=set())

        self.assertEqual(result["status"], "DECIDED")
        self.assertEqual(result["selected"]["id"], "observe")
        self.assertEqual(result["approval_required_options"][0]["id"], "device")
        self.assertEqual(result["approval_required_options"][0]["missing_permissions"], ["device_agent"])

    def test_high_risk_option_requires_explicit_approval_even_if_permission_is_granted(self):
        from brain_v12.brain.decision_engine import DecisionEngine

        options = [
            {"id":"apply_code","action":"apply code","risk":"high","requirements":["developer_approval"],
             "reversible":True,"confidence":0.99},
        ]
        result = DecisionEngine().choose("apply code", options, permissions={"developer_approval"})

        self.assertEqual(result["status"], "WAITING_APPROVAL")
        self.assertEqual(result["selected"]["id"], "apply_code")
        self.assertTrue(result["approval_required"])


if __name__ == "__main__":
    unittest.main()
