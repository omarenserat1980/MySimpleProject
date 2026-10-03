import unittest
from brain_v12.brain.brain_ai_api import BrainAIChatIn
from brain_v12.brain.chat_session_api import SessionCreateIn, MessageIn, router\nfrom brain_v12.brain.chat_session_store import ChatSessionStore\nimport tempfile


class FakeResult:
    ok = True
    reply = "Brain verified reply"
    mode = "test"
    model = "fake"
    tool_calls = []
    evidence = [{"status": "VERIFIED"}]
    error = None


class FakeBrain:
    def chat(self, message, instructions="", approved=False):
        self.last = (message, instructions, approved)
        return FakeResult()


class ChatSessionApiTests(unittest.TestCase):
    def test_models_validate(self):
        self.assertEqual(SessionCreateIn().title, "New Brain Chat")
        self.assertEqual(MessageIn(message="hello").message, "hello")
        self.assertEqual(BrainAIChatIn(message="hello").message, "hello")

    def test_persistent_store_round_trip(self):\n        with tempfile.NamedTemporaryFile() as f:\n            store = ChatSessionStore(f.name); store.init()\n            s = store.create("Persisted")\n            store.add_message(s["id"], "user", "hello")\n            loaded = store.get(s["id"])\n            self.assertEqual(loaded["title"], "Persisted")\n            self.assertEqual(loaded["messages"][0]["content"], "hello")\n\n    def test_context_messages_are_ordered_and_limited(self):
        with tempfile.NamedTemporaryFile() as f:
            store = ChatSessionStore(f.name)
            store.init()
            s = store.create("Context")
            store.add_message(s["id"], "user", "one")
            store.add_message(s["id"], "assistant", "two")
            store.add_message(s["id"], "user", "three")
            items = store.context_messages(s["id"], limit=2)
            self.assertEqual([x["content"] for x in items], ["two", "three"])

    def test_router_builds(self):
        app = router(FakeBrain())
        self.assertTrue(app.routes)


if __name__ == "__main__":
    unittest.main()
