import os
import tempfile
import unittest

from brain_v12.brain.chat_session_api import MessageIn, router
from brain_v12.brain.chat_session_store import ChatSessionStore


class FakeResult:
    ok = True
    reply = "verified"
    mode = "test"
    model = "fake"
    tool_calls = []
    evidence = []
    error = None


class FakeBrain:
    def __init__(self):
        self.calls = []

    def chat(self, message, instructions="", approved=False):
        self.calls.append((message, instructions, approved))
        return FakeResult()


class BrainCardChatIntegrationTests(unittest.TestCase):
    def test_blocked_preflight_prevents_model_call_and_message_persistence(self):
        previous = os.environ.get("BRAIN_EXECUTION_PLANE")
        os.environ["BRAIN_EXECUTION_PLANE"] = "physical"
        try:
            with tempfile.NamedTemporaryFile() as handle:
                store = ChatSessionStore(handle.name)
                store.init()
                session = store.create("blocked")
                brain = FakeBrain()
                endpoint = next(
                    route.endpoint for route in router(brain, store=store).routes
                    if getattr(route, "path", "") == "/api/brain-chat/sessions/{session_id}/messages"
                )
                result = endpoint(
                    session["id"], MessageIn(message="do not process", client_message_id="blocked-1")
                )
                self.assertEqual(result["status"], "BRAIN_PREFLIGHT_BLOCKED")
                self.assertEqual(result["preflight"]["status"], "BLOCKED")
                self.assertEqual(brain.calls, [])
                self.assertEqual(store.context_messages(session["id"]), [])
        finally:
            if previous is None:
                os.environ.pop("BRAIN_EXECUTION_PLANE", None)
            else:
                os.environ["BRAIN_EXECUTION_PLANE"] = previous

    def test_successful_preflight_is_attached_to_chat_evidence(self):
        previous = os.environ.get("BRAIN_EXECUTION_PLANE")
        os.environ["BRAIN_EXECUTION_PLANE"] = "software"
        try:
            with tempfile.NamedTemporaryFile() as handle:
                store = ChatSessionStore(handle.name)
                store.init()
                session = store.create("allowed")
                brain = FakeBrain()
                endpoint = next(
                    route.endpoint for route in router(brain, store=store).routes
                    if getattr(route, "path", "") == "/api/brain-chat/sessions/{session_id}/messages"
                )
                result = endpoint(
                    session["id"], MessageIn(message="hello", client_message_id="allowed-1")
                )
                self.assertTrue(result["ok"])
                self.assertEqual(result["preflight"]["status"], "READY")
                self.assertEqual(len(brain.calls), 1)
                self.assertEqual(result["response"]["preflight_status"], "READY")
                self.assertEqual(
                    result["response"]["brain_card_version"],
                    result["preflight"]["brain_card"]["registry_version"],
                )
        finally:
            if previous is None:
                os.environ.pop("BRAIN_EXECUTION_PLANE", None)
            else:
                os.environ["BRAIN_EXECUTION_PLANE"] = previous


if __name__ == "__main__":
    unittest.main()
