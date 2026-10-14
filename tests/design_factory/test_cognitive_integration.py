import unittest
from brain_v12.brain.cognitive_loop import CognitiveLoop

class FakeStore:
    def __init__(self):
        self._state = {}
        self.events = []
    def state(self):
        return dict(self._state)
    def set_state(self, state):
        self._state = dict(state)
    def event(self, event_type, payload):
        self.events.append({"type": event_type, "payload": payload})
    def memories(self):
        return []
    def save_memory(self, key, value):
        self._memories = getattr(self, "_memories", {})
        self._memories[key] = value

class CognitiveLoopDesignFactoryTests(unittest.TestCase):
    def setUp(self):
        self.store = FakeStore()
        self.loop = CognitiveLoop(self.store)

    def test_tool_is_discoverable_in_live_catalog(self):
        item = next((x for x in self.loop.tool_catalog() if x["id"] == "design.plan"), None)
        self.assertIsNotNone(item)
        self.assertEqual(item["risk"], "low")
        self.assertIsNone(item["permission"])

    def test_tool_routes_through_cognitive_loop_and_returns_plan_only(self):
        result = self.loop.execute_tool(
            "design.plan",
            {"task": "Bitcoin ASIC RTL and OpenROAD physical design"},
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "PLANNED")
        self.assertFalse(result["execution_started"])
        self.assertEqual(result["tool"], "design.plan")
        self.assertIn("G7_PHYSICAL", result["data"]["required_gates"])
        event_types = [event["type"] for event in self.store.events]
        self.assertIn("TOOL_SELECTED", event_types)
        self.assertIn("TOOL_RESULT", event_types)

    def test_missing_task_is_blocked_not_completed(self):
        result = self.loop.execute_tool("design.plan", {})
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["error"], "TASK_DESCRIPTION_REQUIRED")

    def test_live_loop_preserves_ledger_across_authorized_simulation_calls(self):
        planned = self.loop.execute_tool(
            "design.plan",
            {"task": "Bitcoin ASIC RTL and OpenROAD physical design verification"},
        )
        self.assertTrue(planned["ok"])
        ledger = planned["execution_ledger"]
        params = {
            "mode": "step",
            "authorize": True,
            "dry_run": False,
            "executor_mode": "simulation",
        }

        first = self.loop.execute_tool(
            "design.plan", {**params, "execution_ledger": ledger}
        )
        first_ledger = first["execution_ledger"]
        evidence_1 = first_ledger["steps"][0]["evidence"].copy()
        self.assertEqual(first["status"], "PLANNED")
        self.assertEqual(first_ledger["next_step_index"], 1)
        self.assertEqual(first_ledger["steps"][0]["status"], "SIMULATED")

        second = self.loop.execute_tool(
            "design.plan", {**params, "execution_ledger": first_ledger}
        )
        second_ledger = second["execution_ledger"]
        self.assertEqual(second["status"], "PLANNED")
        self.assertEqual(second_ledger["next_step_index"], 2)
        self.assertEqual(second_ledger["steps"][0]["evidence"], evidence_1)
        self.assertEqual(second_ledger["steps"][1]["status"], "SIMULATED")
        self.assertEqual(sum(step["started"] for step in second_ledger["steps"]), 2)
        self.assertFalse(any(step["status"] == "VERIFIED" for step in second_ledger["steps"]))
        event_types = [event["type"] for event in self.store.events]
        self.assertGreaterEqual(event_types.count("TOOL_SELECTED"), 3)
        self.assertGreaterEqual(event_types.count("TOOL_RESULT"), 3)


    def test_design_and_engineering_factories_coexist_in_live_catalog(self):
        ids = {item["id"] for item in self.loop.tool_catalog()}
        self.assertIn("design.plan", ids)
        self.assertIn("engineering.propose", ids)

        result = self.loop.execute_tool(
            "engineering.propose",
            {"problem": "Create a Bitcoin Stratum evidence contract", "evidence": []},
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "COMPLETED")
        self.assertFalse(result["data"]["claims"]["real_mining_verified"])
        event_types = [event["type"] for event in self.store.events]
        self.assertIn("TOOL_SELECTED", event_types)
        self.assertIn("TOOL_RESULT", event_types)

    def test_north_star_blocks_unrelated_goal_before_task_creation(self):
        result = self.loop.run("organize unrelated notes")
        self.assertEqual(result["execution"]["status"], "BLOCKED_MISSION_ALIGNMENT")
        self.assertEqual(result["verification"]["task_status"], "NOT_CREATED")
        self.assertEqual(result["tasks"]["tasks"], [])


if __name__ == "__main__":
    unittest.main()
