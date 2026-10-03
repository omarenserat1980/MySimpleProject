import unittest
from brain_v12.brain.brain_ai_api import BrainAIChatIn
from brain_v12.brain.chat_session_api import SessionCreateIn, MessageIn, router


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

    def test_router_builds(self):
        app = router(FakeBrain())
        self.assertTrue(app.routes)


if __name__ == "__main__":
    unittest.main()
