import unittest

from brain_v12.brain.chatgpt_host_gateway import ChatGPTHostGateway


class TestChatGPTHostGateway(unittest.TestCase):
    def test_without_dispatcher_fails_closed(self):
        result = ChatGPTHostGateway().dispatch("web", {"query": "x"}, "req-1")
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "HOST_DISPATCHER_UNAVAILABLE")

    def test_dispatcher_result_contains_evidence(self):
        def dispatcher(tool, arguments):
            return {
                "ok": True,
                "status": "EXECUTED",
                "result": {"tool": tool, "arguments": arguments},
                "evidence": {"source": "chatgpt-host", "verified": True},
            }

        result = ChatGPTHostGateway(dispatcher).dispatch("web", {"query": "x"}, "req-2")
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "EXECUTED")
        self.assertTrue(result["evidence"]["verified"])

    def test_dispatcher_exception_is_explicit(self):
        def dispatcher(tool, arguments):
            raise RuntimeError("host unavailable")

        result = ChatGPTHostGateway(dispatcher).dispatch("web", {}, "req-3")
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "HOST_DISPATCH_FAILED")

    def test_invalid_dispatcher_result_is_rejected(self):
        result = ChatGPTHostGateway(lambda tool, arguments: "bad").dispatch("web", {}, "req-4")
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "INVALID_HOST_RESULT")


if __name__ == "__main__":
    unittest.main()
