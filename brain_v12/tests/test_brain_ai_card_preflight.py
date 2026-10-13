import unittest
from types import SimpleNamespace

from brain_v12.brain.brain_card_preflight import run_chat_preflight, stable_chat_trace_id


class BrainCardPreflightTests(unittest.TestCase):
    def setUp(self):
        self.brain = SimpleNamespace(chat=lambda *args, **kwargs: None)
        self.store = SimpleNamespace(get=lambda *args: {}, add_message=lambda *args, **kwargs: {})
        self.routes = [SimpleNamespace(
            path="/api/brain-chat/sessions/{session_id}/messages",
            methods={"POST"},
        )]

    def test_ready_report_is_sanitized_and_correlated(self):
        report = run_chat_preflight(
            self.brain, self.store, self.routes,
            trace_id="trace-test", input_kind="chat_message",
        )
        self.assertTrue(report["ok"])
        self.assertEqual(report["status"], "READY")
        self.assertEqual(report["trace_id"], "trace-test")
        self.assertTrue(all("secret" not in str(item).lower() for item in report["checks"]))

    def test_missing_route_blocks(self):
        report = run_chat_preflight(self.brain, self.store, [])
        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "BLOCKED")
        self.assertIn("route.chat_message.registered", report["blocked_reasons"])

    def test_missing_ai_blocks(self):
        report = run_chat_preflight(object(), self.store, self.routes)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertIn("service.brain_ai.callable", report["blocked_reasons"])

    def test_trace_id_is_stable_for_retry_and_does_not_embed_client_id(self):
        first = stable_chat_trace_id("session-1", "client-secret-looking-id")
        second = stable_chat_trace_id("session-1", "client-secret-looking-id")
        self.assertEqual(first, second)
        self.assertNotIn("client-secret-looking-id", first)

    def test_non_software_plane_blocks(self):
        import os
        old = os.environ.get("BRAIN_EXECUTION_PLANE")
        try:
            os.environ["BRAIN_EXECUTION_PLANE"] = "physical"
            report = run_chat_preflight(self.brain, self.store, self.routes)
            self.assertEqual(report["status"], "BLOCKED")
            self.assertIn("policy.software_plane", report["blocked_reasons"])
        finally:
            if old is None:
                os.environ.pop("BRAIN_EXECUTION_PLANE", None)
            else:
                os.environ["BRAIN_EXECUTION_PLANE"] = old


if __name__ == "__main__":
    unittest.main()
