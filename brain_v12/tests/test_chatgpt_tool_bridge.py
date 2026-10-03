import unittest

from brain_v12.brain.chatgpt_tool_bridge import ChatGPTToolBridge, ToolBridgeRequest


class FakeAdapter:
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error
        self.requests = []

    def dispatch(self, request):
        self.requests.append(request)
        if self.error:
            raise self.error
        return self.payload


class TestChatGPTToolBridge(unittest.TestCase):
    def request(self):
        return ToolBridgeRequest(tool="web", arguments={"query": "latest"}, request_id="req-1")

    def test_unconfigured_bridge_fails_closed(self):
        result = ChatGPTToolBridge().dispatch(self.request())
        self.assertFalse(result.ok)
        self.assertEqual(result.status, "BRIDGE_UNAVAILABLE")

    def test_status_reports_fail_closed_delegation(self):
        status = ChatGPTToolBridge().status()
        self.assertFalse(status["available"])
        self.assertTrue(status["evidence_required"])
        self.assertTrue(status["fail_closed"])

    def test_adapter_result_is_returned_with_evidence(self):
        adapter = FakeAdapter({"ok": True, "status": "EXECUTED", "result": {"source": "host"}})
        bridge = ChatGPTToolBridge(adapter)
        result = bridge.dispatch(self.request())
        self.assertTrue(result.ok)
        self.assertEqual(result.status, "EXECUTED")
        self.assertEqual(result.result, {"source": "host"})
        self.assertEqual(adapter.requests[0].request_id, "req-1")

    def test_adapter_failure_is_explicit(self):
        result = ChatGPTToolBridge(FakeAdapter(error=RuntimeError("host unavailable"))).dispatch(self.request())
        self.assertFalse(result.ok)
        self.assertEqual(result.status, "BRIDGE_FAILED")
        self.assertIn("host unavailable", result.error)

    def test_invalid_adapter_result_is_rejected(self):
        result = ChatGPTToolBridge(FakeAdapter("not-an-object")).dispatch(self.request())
        self.assertFalse(result.ok)
        self.assertEqual(result.status, "INVALID_BRIDGE_RESULT")


from brain_v12.brain.chatgpt_tool_bridge import JsonChatGPTToolAdapter, HttpChatGPTToolAdapter, build_chatgpt_tool_bridge_from_environment


class TestJsonChatGPTToolAdapter(unittest.TestCase):
    def test_transport_receives_json_compatible_envelope(self):
        seen = []
        def transport(payload):
            seen.append(payload)
            return {"ok": True, "status": "EXECUTED", "result": {"tool": payload["tool"]}}
        bridge = ChatGPTToolBridge(JsonChatGPTToolAdapter(transport))
        result = bridge.dispatch(ToolBridgeRequest("web", {"query": "x"}, "req-2"))
        self.assertTrue(result.ok)
        self.assertEqual(seen[0]["request_id"], "req-2")
        self.assertEqual(result.result["tool"], "web")

    def test_http_adapter_missing_url_fails_closed(self):
        adapter = HttpChatGPTToolAdapter("")
        with self.assertRaises(RuntimeError):
            adapter.dispatch(ToolBridgeRequest("web", {}, "req-http-1"))

    def test_environment_factory_without_url_is_unavailable(self):
        import os
        previous = os.environ.pop("BRAIN_CHATGPT_BRIDGE_URL", None)
        try:
            bridge = build_chatgpt_tool_bridge_from_environment()
            self.assertFalse(bridge.available)
            self.assertEqual(bridge.status()["transport"], None)
        finally:
            if previous is not None:
                os.environ["BRAIN_CHATGPT_BRIDGE_URL"] = previous

    def test_missing_transport_fails_closed(self):
        bridge = ChatGPTToolBridge(JsonChatGPTToolAdapter(None))
        result = bridge.dispatch(ToolBridgeRequest("web", {}, "req-3"))
        self.assertFalse(result.ok)
        self.assertEqual(result.status, "BRIDGE_FAILED")


if __name__ == "__main__":
    unittest.main()
