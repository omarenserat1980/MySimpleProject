import json
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from brain_v12.brain.brain_mcp import PROTOCOL_VERSION, build_mcp_router


class _BrainAI:
    def status(self):
        return {"ready": True}


class _DeviceBridge:
    def agent_status(self):
        return {"enabled": False, "agents": []}


class _Store:
    pass


class BrainMCPCommunicationChannelTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(build_mcp_router(_BrainAI(), _DeviceBridge(), _Store()))
        self.client = TestClient(app)
        self._env = patch.dict("os.environ", {"BRAIN_MCP_TOKEN": "unit-test-token"})
        self._env.start()
        self.headers = {"MCP-Protocol-Version": PROTOCOL_VERSION, "Authorization": "Bearer unit-test-token"}

    def tearDown(self):
        self._env.stop()

    def _call_tool(self, name, arguments=None):
        response = self.client.post(
            "/mcp",
            headers=self.headers,
            json={
                "jsonrpc": "2.0",
                "id": 7,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments or {}},
            },
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["result"]["structuredContent"]

    def test_mcp_requires_configured_bearer_token(self):
        with patch.dict("os.environ", {}, clear=True):
            response = self.client.get("/mcp")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "MCP_NOT_CONFIGURED")

    def test_initialize_negotiates_protocol_version_from_json_rpc_params(self):
        response = self.client.post(
            "/mcp",
            headers={"Authorization": "Bearer unit-test-token"},
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "unit-test", "version": "1"},
                },
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"]["protocolVersion"], PROTOCOL_VERSION)

    def test_tools_list_exposes_channel_inventory_and_render_cat_probe(self):
        response = self.client.post(
            "/mcp",
            headers=self.headers,
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        )
        self.assertEqual(response.status_code, 200)
        names = {tool["name"] for tool in response.json()["result"]["tools"]}
        self.assertIn("brain.communication_channels", names)
        self.assertIn("brain.render_cat_probe", names)

    def test_channel_inventory_is_read_only_and_marks_mouse_as_emulator(self):
        result = self._call_tool("brain.communication_channels")
        self.assertTrue(result["ok"])
        self.assertFalse(result["external_side_effects"])
        by_id = {item["id"]: item for item in result["channels"]}
        self.assertEqual(by_id["brain-mouse"]["status"], "LOCAL_EMULATOR_ONLY")
        self.assertEqual(by_id["render-cat"]["status"], "NOT_CONFIGURED")

    def test_render_cat_probe_fails_closed_without_configuration(self):
        with patch.dict("os.environ", {"BRAIN_RENDER_CAT_BASE_URL": ""}):
            result = self._call_tool("brain.render_cat_probe", {"path": "/health"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "NOT_CONFIGURED")
        self.assertFalse(result["external_side_effects"])

    def test_render_cat_probe_rejects_non_allowlisted_path_without_network(self):
        result = self._call_tool("brain.render_cat_probe", {"path": "/deploy"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "PATH_NOT_ALLOWED")


if __name__ == "__main__":
    unittest.main()
