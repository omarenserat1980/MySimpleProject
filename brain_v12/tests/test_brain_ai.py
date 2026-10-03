import unittest

from brain_v12.brain.brain_ai import BrainAI


class FakeProvider:
    def status(self):
        return {"provider": "fake", "configured": True, "model": "test"}

    def respond(self, user_text, context="", instructions=""):
        return {"ok": True, "provider": "fake", "model": "test",
                "reply": f"Brain received: {user_text}",
                "response_id": "test-response"}


class FakeMemory:
    def memories(self):
        return [{"key": "project", "value": "Electronic Brain"}]


class TestBrainAI(unittest.TestCase):
    def setUp(self):
        self.ai = BrainAI(FakeProvider(), FakeMemory(), None)

    def test_status_exposes_brain_layer(self):
        data = self.ai.status()
        self.assertEqual(data["name"], "Brain AI")
        self.assertTrue(data["memory_enabled"])

    def test_chat_returns_provider_evidence(self):
        result = self.ai.chat("مرحبا")
        self.assertTrue(result.ok)
        self.assertIn("Brain received", result.reply)
        self.assertEqual(result.evidence[0]["response_id"], "test-response")

    def test_high_risk_tool_requires_approval(self):
        self.ai.register_tool("danger", "test", lambda _: {"ok": True}, risk="high")
        result = self.ai.execute_tool("danger")
        self.assertEqual(result["status"], "WAITING_APPROVAL")

    def test_tool_result_is_explicit(self):
        self.ai.register_tool("status", "test",
                              lambda _: {"ok": True, "status": "COMPLETED"})
        result = self.ai.execute_tool("status")
        self.assertEqual(result["status"], "COMPLETED")

    def test_full_github_tool_surface_is_registered(self):
        from brain_v12.github_capability_registry import GITHUB_TOOLS
        for name in GITHUB_TOOLS:
            self.assertIn("github.tool." + name, self.ai.tools)
        self.assertEqual(sum(1 for name in self.ai.tools if name.startswith("github.tool.")), len(GITHUB_TOOLS))

    def test_github_mutation_surface_remains_approval_gated(self):
        result = self.ai.execute_tool("github.tool.update_file", {"method": "PUT", "path": "/repos/o/r/contents/x"})
        self.assertEqual(result["status"], "WAITING_APPROVAL")


if __name__ == "__main__":
    unittest.main()
