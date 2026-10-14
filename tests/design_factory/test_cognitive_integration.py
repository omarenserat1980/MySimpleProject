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

if __name__ == "__main__":
    unittest.main()
