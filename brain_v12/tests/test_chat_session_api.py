import tempfile
import unittest

from brain_v12.brain.brain_ai_api import BrainAIChatIn
from brain_v12.brain.chat_session_api import MemoryIn, MessageIn, SessionCreateIn, router
from brain_v12.brain.chat_session_store import ChatSessionStore


class FakeResult:
    ok = True
    reply = "Brain verified reply"
    mode = "test"
    model = "fake"
    tool_calls = []
    evidence = [{"status": "VERIFIED"}]
    error = None


class FakeBrain:
    def __init__(self):
        self.calls = []

    def chat(self, message, instructions="", approved=False):
        self.last = (message, instructions, approved)
        self.calls.append(self.last)
        return FakeResult()


class ChatSessionApiTests(unittest.TestCase):
    def test_models_validate(self):
        self.assertEqual(SessionCreateIn().title, "New Brain Chat")
        self.assertEqual(MessageIn(message="hello").message, "hello")
        self.assertEqual(MemoryIn(summary="x").summary, "x")
        self.assertEqual(BrainAIChatIn(message="hello").message, "hello")

    def test_persistent_store_round_trip(self):
        with tempfile.NamedTemporaryFile() as f:
            store = ChatSessionStore(f.name)
            store.init()
            s = store.create("Persisted")
            store.add_message(s["id"], "user", "hello")
            loaded = store.get(s["id"])
            self.assertEqual(loaded["title"], "Persisted")
            self.assertEqual(loaded["messages"][0]["content"], "hello")
            self.assertEqual(loaded["memory"]["summary"], "")

    def test_session_memory_is_persistent_and_isolated(self):
        with tempfile.NamedTemporaryFile() as f:
            store = ChatSessionStore(f.name)
            store.init()
            first = store.create("First")
            second = store.create("Second")
            store.set_memory(first["id"], "first-session facts")
            self.assertEqual(store.get_memory(first["id"])["summary"], "first-session facts")
            self.assertEqual(store.get_memory(second["id"])["summary"], "")

    def test_context_messages_are_ordered_and_limited(self):
        with tempfile.NamedTemporaryFile() as f:
            store = ChatSessionStore(f.name)
            store.init()
            s = store.create("Context")
            store.add_message(s["id"], "user", "one")
            store.add_message(s["id"], "assistant", "two")
            store.add_message(s["id"], "user", "three")
            items = store.context_messages(s["id"], limit=2)
            self.assertEqual([x["content"] for x in items], ["two", "three"])

    def test_long_conversation_compaction_preserves_recent_window(self):
        with tempfile.NamedTemporaryFile() as f:
            store = ChatSessionStore(f.name)
            store.init()
            s = store.create("Long")
            for i in range(5):
                store.add_message(s["id"], "user", "message-{}".format(i))
            result = store.compact_session(s["id"], keep_recent=2, max_summary_chars=1000)
            self.assertTrue(result["compacted"])
            self.assertEqual(result["older_messages"], 3)
            self.assertIn("message-0", result["summary"])
            self.assertIn("message-2", result["summary"])
            self.assertNotIn("message-3", result["summary"])
            recent = store.context_messages(s["id"], limit=2)
            self.assertEqual([x["content"] for x in recent], ["message-3", "message-4"])
            self.assertLessEqual(len(store.get_memory(s["id"])["summary"]), 1000)

    def test_compaction_is_session_isolated(self):
        with tempfile.NamedTemporaryFile() as f:
            store = ChatSessionStore(f.name)
            store.init()
            first = store.create("First")
            second = store.create("Second")
            for i in range(3):
                store.add_message(first["id"], "user", "first-{}".format(i))
            store.add_message(second["id"], "user", "second-only")
            store.compact_session(first["id"], keep_recent=1)
            self.assertIn("first-0", store.get_memory(first["id"])["summary"])
            self.assertEqual(store.get_memory(second["id"])["summary"], "")

    def test_sync_event_feed_is_ordered_and_cursor_based(self):
        with tempfile.NamedTemporaryFile() as f:
            store = ChatSessionStore(f.name)
            store.init()
            s = store.create("Sync")
            store.add_message(s["id"], "user", "hello")
            store.add_message(s["id"], "assistant", "world")
            first = store.sync_events(s["id"], after=0, limit=2)
            self.assertEqual([e["event_type"] for e in first["events"]], ["SESSION_CREATED", "MESSAGE_ADDED"])
            self.assertTrue(first["has_more"])
            second = store.sync_events(s["id"], after=first["next_cursor"], limit=10)
            self.assertEqual([e["event_type"] for e in second["events"]], ["MESSAGE_ADDED"])
            self.assertGreater(second["next_cursor"], first["next_cursor"])

    def test_duplicate_client_message_is_idempotent(self):
        with tempfile.NamedTemporaryFile() as f:
            store = ChatSessionStore(f.name)
            store.init()
            s = store.create("Idempotent")
            first = store.add_message(s["id"], "user", "hello", client_message_id="client-1")
            second = store.add_message(s["id"], "user", "hello", client_message_id="client-1")
            self.assertEqual(len(first["messages"]), 1)
            self.assertEqual(len(second["messages"]), 1)
            feed = store.sync_events(s["id"])
            message_events = [e for e in feed["events"] if e["event_type"] == "MESSAGE_ADDED"]
            self.assertEqual(len(message_events), 1)

    def test_sync_event_feed_is_session_isolated(self):
        with tempfile.NamedTemporaryFile() as f:
            store = ChatSessionStore(f.name)
            store.init()
            first = store.create("First")
            second = store.create("Second")
            store.add_message(first["id"], "user", "only-first")
            feed = store.sync_events(second["id"])
            self.assertEqual([e["event_type"] for e in feed["events"]], ["SESSION_CREATED"])
            self.assertEqual(feed["events"][0]["payload"]["title"], "Second")
            self.assertNotIn("only-first", str(feed["events"]))

    def test_same_account_sessions_are_visible_across_devices(self):
        with tempfile.NamedTemporaryFile() as f:
            store = ChatSessionStore(f.name)
            store.init()
            phone = store.create("Phone Chat", account_id="account-1", device_id="phone")
            desktop = store.create("Desktop Chat", account_id="account-1", device_id="desktop")
            other = store.create("Other Account", account_id="account-2", device_id="tablet")
            visible = store.list(account_id="account-1")
            ids = {x["id"] for x in visible}
            self.assertEqual(ids, {phone["id"], desktop["id"]})
            self.assertNotIn(other["id"], ids)

    def test_router_builds(self):
        app = router(FakeBrain())
        self.assertTrue(app.routes)

    def test_message_endpoint_replays_completed_request_without_second_ai_call(self):
        with tempfile.NamedTemporaryFile() as f:
            store = ChatSessionStore(f.name)
            store.init()
            session = store.create("API idempotency")
            brain = FakeBrain()
            endpoint = next(route.endpoint for route in router(brain, store=store).routes
                            if getattr(route, "path", "") == "/api/brain-chat/sessions/{session_id}/messages")
            body = MessageIn(message="hello", client_message_id="retry-1", device_id="phone")
            first = endpoint(session["id"], body)
            second = endpoint(session["id"], body)
            self.assertEqual(len(brain.calls), 1)
            self.assertFalse(first["idempotent_replay"])
            self.assertTrue(second["idempotent_replay"])
            self.assertEqual(first["response"], second["response"])
            user_messages = [m for m in second["session"]["messages"] if m["role"] == "user"]
            assistant_messages = [m for m in second["session"]["messages"] if m["role"] == "assistant"]
            self.assertEqual(len(user_messages), 1)
            self.assertEqual(len(assistant_messages), 1)

    def test_message_endpoint_recovers_reply_persisted_before_ledger_completion(self):
        with tempfile.NamedTemporaryFile() as f:
            store = ChatSessionStore(f.name)
            store.init()
            session = store.create("Crash recovery")
            brain = FakeBrain()
            endpoint = next(route.endpoint for route in router(brain, store=store).routes
                            if getattr(route, "path", "") == "/api/brain-chat/sessions/{session_id}/messages")
            body = MessageIn(message="hello", client_message_id="crash-window-1")
            first = endpoint(session["id"], body)
            self.assertTrue(first["ok"])
            self.assertEqual(len(brain.calls), 1)

            # Simulate a process crash after the assistant message was committed
            # but before the idempotency ledger could persist its cached response.
            with store.connect() as con:
                con.execute(
                    "UPDATE chat_request_idempotency SET status='PROCESSING',response_json=NULL "
                    "WHERE session_id=? AND client_message_id=?",
                    (session["id"], "crash-window-1"),
                )
                con.commit()

            recovered = endpoint(session["id"], body)
            self.assertTrue(recovered["idempotent_replay"])
            self.assertEqual(recovered["response"]["content"], "Brain verified reply")
            self.assertEqual(len(brain.calls), 1)
            messages = recovered["session"]["messages"]
            self.assertEqual(sum(1 for m in messages if m["role"] == "assistant"), 1)

    def test_message_endpoint_rejects_reused_id_with_changed_payload(self):
        with tempfile.NamedTemporaryFile() as f:
            store = ChatSessionStore(f.name)
            store.init()
            session = store.create("API id conflict")
            brain = FakeBrain()
            endpoint = next(route.endpoint for route in router(brain, store=store).routes
                            if getattr(route, "path", "") == "/api/brain-chat/sessions/{session_id}/messages")
            first = endpoint(session["id"], MessageIn(message="hello", client_message_id="same-id"))
            conflict = endpoint(session["id"], MessageIn(message="different", client_message_id="same-id"))
            self.assertTrue(first["ok"])
            self.assertEqual(conflict["status"], "CLIENT_MESSAGE_ID_CONFLICT")
            self.assertEqual(len(brain.calls), 1)


if __name__ == "__main__":
    unittest.main()
