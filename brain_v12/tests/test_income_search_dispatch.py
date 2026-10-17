import os
import tempfile
import unittest

from brain_v12.brain.client_suggestion_bridge import ClientSuggestionBridge


class FakeChatGPT:
    def respond(self, **kwargs):
        return {"ok": True, "provider": "test", "model": "fake", "reply": "Search public opportunities."}


class FakeDecisionEngine:
    def generate(self, suggestion):
        return [{"id": "income_opportunities", "tool_id": "income.search"}]

    def choose(self, suggestion, options, permissions=None):
        return {"status": "DECIDED", "selected": options[0], "north_star": {"status": "NOT_APPLICABLE"}}


class IncomeSearchDispatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "bridge.sqlite")
        self.calls = []
        self.search_result = {"ok": True, "received": 3, "accepted": 2, "errors": [], "retrieved_at": "test"}
        self.bridge = ClientSuggestionBridge(
            self.db, FakeChatGPT(), FakeDecisionEngine(),
            lambda client_id, action: self._request_action(client_id, action),
            income_searcher=lambda: self._search(),
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _search(self):
        self.calls.append("search")
        return self.search_result

    def _request_action(self, client_id, action):
        self.calls.append(("action", action))
        return {"accepted": True, "task_id": "task-test"}

    def test_income_search_is_run_and_evidence_summary_is_forwarded(self):
        result = self.bridge.submit("CL-000003", "ابحث عن فرص دخل مدفوعة")
        self.assertEqual(result["status"], "ACTION_REQUESTED")
        self.assertEqual(self.calls[0], "search")
        action = self.calls[1][1]
        self.assertEqual(action["income_search"]["accepted"], 2)
        self.assertFalse(action["income_search"]["revenue_verified"])
        self.assertFalse(result["revenue_verified"])

    def test_search_failure_does_not_queue_an_action(self):
        self.search_result = {"ok": False, "status": "NETWORK_FAILED"}
        result = self.bridge.submit("CL-000003", "ابحث عن فرص دخل مدفوعة")
        self.assertEqual(result["status"], "INCOME_SEARCH_FAILED")
        self.assertEqual(self.calls, ["search"])


if __name__ == "__main__":
    unittest.main()
