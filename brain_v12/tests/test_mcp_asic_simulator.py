import json
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from brain_v12.brain.brain_mcp import PROTOCOL_VERSION, build_mcp_router


class FakeBrainAI:
    def status(self):
        return {"ok": True}


class FakeDeviceBridge:
    def agent_status(self):
        return {"configured": False}


class MCPASICSimulatorTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(build_mcp_router(FakeBrainAI(), FakeDeviceBridge(), object()))
        self.client = TestClient(app)
        self.headers = {"MCP-Protocol-Version": PROTOCOL_VERSION}

    def rpc(self, method, params=None, request_id=1):
        return self.client.post(
            "/mcp",
            headers=self.headers,
            json={"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}},
        )

    def test_initialize_and_tool_discovery_include_asic(self):
        initialized = self.rpc("initialize")
        self.assertEqual(initialized.status_code, 200)
        self.assertEqual(initialized.json()["result"]["protocolVersion"], PROTOCOL_VERSION)

        listed = self.rpc("tools/list")
        self.assertEqual(listed.status_code, 200)
        names = {tool["name"] for tool in listed.json()["result"]["tools"]}
        self.assertIn("brain.asic_simulate", names)

    def test_asic_tool_runs_through_existing_brain_api_handler(self):
        result = self.rpc(
            "tools/call",
            {
                "name": "brain.asic_simulate",
                "arguments": {
                    "netlist": {
                        "nodes": [
                            {"name": "a", "op": "INPUT"},
                            {"name": "b", "op": "INPUT"},
                            {"name": "y", "op": "XOR", "inputs": ["a", "b"]},
                        ],
                        "outputs": ["y"],
                    },
                    "vectors": [{"a": 0, "b": 1}, {"a": 1, "b": 1}],
                    "max_cycles": 2,
                },
            },
        )
        self.assertEqual(result.status_code, 200)
        payload = result.json()["result"]["structuredContent"]
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["source"], "brain-api:/api/asic-sim/run")
        self.assertEqual(payload["execution_mode"], "SOFTWARE_SIMULATOR")
        self.assertFalse(payload["physical_hardware_access"])
        self.assertEqual([row["outputs"]["y"] for row in payload["trace"]], [1, 0])

    def test_asic_tool_rejects_invalid_vectors_without_claiming_success(self):
        result = self.rpc(
            "tools/call",
            {
                "name": "brain.asic_simulate",
                "arguments": {
                    "netlist": {"nodes": [{"name": "a", "op": "INPUT"}], "outputs": ["a"]},
                    "vectors": [{"not_a": 1}],
                },
            },
        )
        self.assertEqual(result.status_code, 200)
        payload = result.json()["result"]["structuredContent"]
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["status"], "ASIC_SIMULATION_REJECTED")
        self.assertEqual(payload["execution_mode"], "SOFTWARE_SIMULATOR")


if __name__ == "__main__":
    unittest.main()
