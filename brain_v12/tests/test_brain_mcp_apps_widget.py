import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from fastapi import Request

from brain_v12.brain.brain_mcp import WIDGET_URI, build_mcp_router
from brain_v12.brain.chat_session_store import ChatSessionStore


class FakeResult:
    ok = True
    reply = "رد تجريبي من العقل"
    mode = "test"
    model = "fake"
    tool_calls = []
    evidence = [{"type": "test", "status": "VERIFIED"}]
    error = None


class FakeBrain:
    def __init__(self):
        self.calls = []

    def status(self):
        return {"configured": True}

    def chat(self, message, instructions="", approved=False):
        self.calls.append((message, instructions, approved))
        return FakeResult()


class FakeDeviceBridge:
    def agent_status(self):
        return {"configured": False, "agents": []}


class FakeMemoryStore:
    path = ":memory:"


class BrainMcpAppsWidgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.chat_store = ChatSessionStore(Path(self.temp.name) / "chat.db")
        self.chat_store.init()
        self.brain = FakeBrain()
        router = build_mcp_router(
            self.brain,
            FakeDeviceBridge(),
            FakeMemoryStore(),
            chat_sessions=self.chat_store,
        )
        self.post = next(
            route.endpoint
            for route in router.routes
            if getattr(route, "path", "") == "/mcp" and "POST" in getattr(route, "methods", set())
        )

    def tearDown(self):
        self.temp.cleanup()

    def rpc(self, payload):
        async def run():
            body = json.dumps(payload).encode("utf-8")
            sent = False

            async def receive():
                nonlocal sent
                if sent:
                    return {"type": "http.request", "body": b"", "more_body": False}
                sent = True
                return {"type": "http.request", "body": body, "more_body": False}

            request = Request(
                {
                    "type": "http",
                    "http_version": "1.1",
                    "method": "POST",
                    "scheme": "https",
                    "path": "/mcp",
                    "raw_path": b"/mcp",
                    "query_string": b"",
                    "headers": [(b"mcp-protocol-version", b"2026-07-28")],
                    "server": ("testserver", 443),
                    "client": ("testclient", 1234),
                },
                receive,
            )
            response = await self.post(request)
            return json.loads(response.body.decode("utf-8"))

        return asyncio.run(run())

    def tool(self, name, arguments=None, request_id=1):
        return self.rpc(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments or {}},
            }
        )["result"]["structuredContent"]

    def test_tools_list_exposes_render_tool_with_mcp_apps_metadata(self):
        response = self.rpc({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        tools = {item["name"]: item for item in response["result"]["tools"]}
        widget_tool = tools["brain.open_chat_widget"]
        self.assertEqual(widget_tool["_meta"]["ui"]["resourceUri"], WIDGET_URI)
        self.assertEqual(widget_tool["_meta"]["openai/outputTemplate"], WIDGET_URI)

    def test_widget_resource_is_readable_and_contains_safe_cycle_controls(self):
        listing = self.rpc({"jsonrpc": "2.0", "id": 1, "method": "resources/list"})
        self.assertEqual(listing["result"]["resources"][0]["uri"], WIDGET_URI)
        result = self.rpc(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "resources/read",
                "params": {"uri": WIDGET_URI},
            }
        )
        html = result["result"]["contents"][0]["text"]
        self.assertIn('lang="ar" dir="rtl"', html)
        self.assertIn('id="pause"', html)
        self.assertIn('id="resume"', html)
        self.assertIn('id="stop"', html)
        self.assertIn("MAX_CYCLES = 5", html)
        self.assertIn('await sendAin()', html)

    def test_session_create_is_idempotent_for_same_cycle_key(self):
        args = {"title": "دورة ع 1", "client_session_key": "run-1:1"}
        first = self.tool("brain.chat_session_create", args, 10)
        second = self.tool("brain.chat_session_create", args, 11)
        self.assertEqual(first["session"]["id"], second["session"]["id"])
        self.assertFalse(first["idempotent_replay"])
        self.assertTrue(second["idempotent_replay"])

    def test_chat_send_is_idempotent_and_never_approves_external_actions(self):
        session = self.tool(
            "brain.chat_session_create",
            {"title": "Test", "client_session_key": "run-2:1"},
            20,
        )["session"]
        args = {
            "session_id": session["id"],
            "message": "ع",
            "client_message_id": "run-2:1:ain",
        }
        first = self.tool("brain.chat_session_send", args, 21)
        second = self.tool("brain.chat_session_send", args, 22)
        self.assertEqual(first["response"]["content"], "رد تجريبي من العقل")
        self.assertTrue(second["idempotent_replay"])
        self.assertEqual(len(self.brain.calls), 1)
        self.assertFalse(self.brain.calls[0][2])

    def test_invalid_chat_send_does_not_call_brain(self):
        result = self.tool(
            "brain.chat_session_send",
            {"session_id": "", "message": "ع", "client_message_id": "x"},
            30,
        )
        self.assertEqual(result["status"], "INVALID_CHAT_MESSAGE")
        self.assertEqual(self.brain.calls, [])


if __name__ == "__main__":
    unittest.main()
