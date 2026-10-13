import os
import tempfile
import unittest

from brain_v12.brain.brain_ai_api import BrainAIChatIn, BrainAIToolIn, router as brain_ai_router
from brain_v12.brain.chat_session_api import MessageIn, router as chat_router
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
        self.tools = []

    def chat(self, message, instructions="", approved=False):
        self.calls.append((message, instructions, approved))
        return FakeResult()

    def execute_tool(self, name, params, approved=False):
        self.tools.append((name, params, approved))
        return {"ok": True, "status": "SIMULATED", "tool": name}


class BrainCardChatIntegrationTests(unittest.TestCase):
    def _set_plane(self, value):
        previous = os.environ.get("BRAIN_EXECUTION_PLANE")
        os.environ["BRAIN_EXECUTION_PLANE"] = value
        return previous

    def _restore_plane(self, previous):
        if previous is None:
            os.environ.pop("BRAIN_EXECUTION_PLANE", None)
        else:
            os.environ["BRAIN_EXECUTION_PLANE"] = previous

    def test_blocked_preflight_prevents_model_call_and_message_persistence(self):
        previous = self._set_plane("physical")
        try:
            with tempfile.NamedTemporaryFile() as handle:
                store = ChatSessionStore(handle.name)
                store.init()
                session = store.create("blocked")
                brain = FakeBrain()
                endpoint = next(
                    route.endpoint for route in chat_router(brain, store=store).routes
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
            self._restore_plane(previous)

    def test_successful_preflight_is_attached_to_chat_evidence(self):
        previous = self._set_plane("software")
        try:
            with tempfile.NamedTemporaryFile() as handle:
                store = ChatSessionStore(handle.name)
                store.init()
                session = store.create("allowed")
                brain = FakeBrain()
                endpoint = next(
                    route.endpoint for route in chat_router(brain, store=store).routes
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
            self._restore_plane(previous)

    def test_direct_brain_ai_chat_is_gated(self):
        previous = self._set_plane("physical")
        try:
            brain = FakeBrain()
            endpoint = next(
                route.endpoint for route in brain_ai_router(brain).routes
                if getattr(route, "path", "") == "/api/brain-ai/chat"
            )
            result = endpoint(BrainAIChatIn(message="must not process"))
            self.assertEqual(result["status"], "BRAIN_PREFLIGHT_BLOCKED")
            self.assertEqual(brain.calls, [])
        finally:
            self._restore_plane(previous)

    def test_direct_tool_dispatch_is_gated(self):
        previous = self._set_plane("physical")
        try:
            brain = FakeBrain()
            endpoint = next(
                route.endpoint for route in brain_ai_router(brain).routes
                if getattr(route, "path", "") == "/api/brain-ai/tool"
            )
            result = endpoint(BrainAIToolIn(name="github.simulator", params={"task": "status"}))
            self.assertEqual(result["status"], "BRAIN_PREFLIGHT_BLOCKED")
            self.assertEqual(brain.tools, [])
        finally:
            self._restore_plane(previous)

    def test_direct_tool_dispatch_runs_only_after_preflight_passes(self):
        previous = self._set_plane("software")
        try:
            brain = FakeBrain()
            endpoint = next(
                route.endpoint for route in brain_ai_router(brain).routes
                if getattr(route, "path", "") == "/api/brain-ai/tool"
            )
            result = endpoint(BrainAIToolIn(name="github.simulator", params={"task": "status"}))
            self.assertEqual(result["preflight"]["status"], "READY")
            self.assertEqual(len(brain.tools), 1)
            self.assertEqual(result["status"], "SIMULATED")
        finally:
            self._restore_plane(previous)


if __name__ == "__main__":
    unittest.main()
