import unittest
from types import SimpleNamespace
from brain_v12.brain.streaming_api import iter_text, stream_result


class StreamingApiTests(unittest.TestCase):
    def test_iter_text_preserves_full_response(self):
        self.assertEqual("".join(iter_text("abcdefgh", 3)), "abcdefgh")

    def test_stream_result_emits_start_deltas_done(self):
        result = SimpleNamespace(ok=True, reply="hello world", model="test-model")
        output = "".join(stream_result(result, 4))
        self.assertIn("event: start", output)
        self.assertIn('event: delta', output)
        self.assertIn("hello", output)
        self.assertIn("world", output)
        self.assertIn("event: done", output)

    def test_stream_result_emits_error_and_done(self):
        output = "".join(stream_result({"ok": False, "error": "PROVIDER_FAILED"}))
        self.assertIn("event: error", output)
        self.assertIn("PROVIDER_FAILED", output)
        self.assertIn("event: done", output)


if __name__ == "__main__":
    unittest.main()
