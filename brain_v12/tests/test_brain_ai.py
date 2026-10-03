import unittest

from brain_v12.brain.brain_ai import BrainAI


class FakeProvider:
    def __init__(self, tool=False):
        self.tool = tool
        self.calls = 0

    def status(self):
        return {"provider": "fake", "configured": True, "model": "test"}

    def respond(self, user_text, context="", instructions=""):
        self.calls += 1
        if self.tool and self.calls == 1:
            return {
                "ok": True, "provider": "fake", "model": "test",
                "reply": '{"type":"tool_call","call_id":"c1","name":"echo","arguments":{"x":7}}',
                "response_id": "tool-request",
            }
        return {
            "ok": True, "provider": "fake", "model": "test",
            "reply": "tool result verified",
            "response_id": f"response-{self.calls}",
        }


class FakeMemory:
    def memories(self):
        return [{"key": "project", "value": "Electronic Brain"}]


class TestBrainAI(unittest.TestCase):
    def test_status(self):
        ai = BrainAI(FakeProvider(), FakeMemory(), None)
        data = ai.status()
        self.assertEqual(data["name"], "Brain AI")
        self.assertTrue(data["memory_enabled"])
        self.assertTrue(data["tool_calling"]["enabled"])

    def test_normal_chat(self):
        ai = BrainAI(FakeProvider(), FakeMemory(), None)
        result = ai.chat("مرحبا")
        self.assertTrue(result.ok)
        self.assertEqual(result.evidence[0]["response_id"], "response-1")

    def test_high_risk_requires_approval(self):
        ai = BrainAI(FakeProvider(), FakeMemory(), None)
        ai.register_tool("danger", "test", lambda _: {"value": 1}, risk="high")
        result = ai.execute_tool("danger")
        self.assertEqual(result["status"], "WAITING_APPROVAL")

    def test_real_tool_call_executes_and_finalizes(self):
        provider = FakeProvider(tool=True)
        ai = BrainAI(provider, FakeMemory(), None)
        ai.register_tool("echo", "echo input", lambda p: {"value": p["x"]})
        result = ai.chat("نفذ echo")
        self.assertTrue(result.ok)
        self.assertEqual(result.mode, "tool_executed")
        self.assertEqual(result.reply, "tool result verified")
        self.assertEqual(result.tool_calls[0]["name"], "echo")
        self.assertEqual(result.tool_calls[0]["status"], "SUCCESS")
        self.assertEqual(result.evidence[1]["type"], "tool")
        self.assertEqual(result.evidence[1]["result"]["value"], 7)
        self.assertEqual(provider.calls, 2)

    def test_unknown_tool_is_rejected_with_evidence(self):
        provider = FakeProvider(tool=True)
        ai = BrainAI(provider, FakeMemory(), None)
        result = ai.chat("نفذ")
        self.assertFalse(result.ok)
        self.assertEqual(result.error, "UNKNOWN_TOOL")
        self.assertEqual(result.evidence[1]["status"], "UNKNOWN_TOOL")


if __name__ == "__main__":
    unittest.main()
