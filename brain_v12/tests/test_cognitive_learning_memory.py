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
                "VERIFIED_SUCCESS", "ACTION_VERIFIED_NOT_GOAL",
                "WAITING_PERMISSION", "FAILED_OR_UNVERIFIED"
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



    def test_execution_uses_the_tool_selected_by_the_decision(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(str(Path(directory) / "brain.db"))
            store.init()
            result = CognitiveLoop(store).run("review current state safely")

            self.assertEqual(result["decision"]["selected"]["tool_id"], "state.read")
            self.assertEqual(result["execution"]["tool"], "state.read")
            self.assertTrue(result["execution"]["tool_result"]["ok"])

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
        self.assertEqual(result["selected"]["decision_score_breakdown"]["base_confidence"], 0.7)
        self.assertEqual(result["selected"]["decision_score"], 0.7)

    def test_only_caller_approved_action_id_satisfies_high_risk_approval(self):
        from brain_v12.brain.decision_engine import DecisionEngine

        options = [
            {"id":"apply_code","action":"apply code","risk":"high","requirements":[],
             "reversible":True,"confidence":0.99},
        ]
        result = DecisionEngine().choose(
            "apply code", options, permissions=set(), approved_actions={"apply_code"}
        )
        self.assertEqual(result["status"], "DECIDED")
        self.assertEqual(result["selected"]["id"], "apply_code")

    def test_legacy_tool_success_does_not_count_as_verified_goal_memory(self):
        import json
        from brain_v12.brain.decision_engine import DecisionEngine

        legacy = {
            "key": "cognitive.run.legacy",
            "value": json.dumps({
                "goal": "inspect repository status",
                "action": "observe",
                "outcome": "VERIFIED_SUCCESS",
                "verified": True,
                "verification_status": "VERIFIED",
            }),
        }
        self.assertFalse(
            DecisionEngine._has_verified_similar_success(
                "inspect repository status", "observe", [legacy]
            )
        )

    def test_high_risk_option_requires_explicit_approval_even_if_permission_is_granted(self):
        from brain_v12.brain.decision_engine import DecisionEngine

        options = [
            {"id":"apply_code","action":"apply code","risk":"high","requirements":["developer_approval"],
             "reversible":True,"confidence":0.99},
        ]
        result = DecisionEngine().choose(
            "apply code", options, permissions={"developer_approval"}, approved_actions=set()
        )

        self.assertEqual(result["status"], "WAITING_APPROVAL")
        self.assertEqual(result["selected"]["id"], "apply_code")
        self.assertTrue(result["approval_required"])


if __name__ == "__main__":
    unittest.main()
