"""MCP integration tests for the shared SHA-256d evidence contract."""
import json
import unittest
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from brain_v12.brain.brain_mcp import PROTOCOL_VERSION, build_mcp_router
from brain_v12.brain.sha256d_execution_contract import make_layer_result


class Sha256dMcpContractTests(unittest.TestCase):
    def setUp(self):
        brain_ai = SimpleNamespace(status=lambda: {"status": "READY"})
        device_bridge = SimpleNamespace(agent_status=lambda: {"online": False})
        store = SimpleNamespace()
        app = FastAPI()
        app.include_router(build_mcp_router(brain_ai, device_bridge, store))
        self.client = TestClient(app)
        self.headers = {"MCP-Protocol-Version": PROTOCOL_VERSION}

    def test_sha256d_tool_is_discoverable(self):
        response = self.client.post("/mcp", headers=self.headers, json={
            "jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {},
        })
        self.assertEqual(response.status_code, 200)
        names = [tool["name"] for tool in response.json()["result"]["tools"]]
        self.assertIn("brain.sha256d_layers", names)

    def test_sha256d_run_rtl_tool_is_discoverable_and_fail_closed(self):
        listed = self.client.post("/mcp", headers=self.headers, json={
            "jsonrpc": "2.0", "id": 10, "method": "tools/list", "params": {},
        })
        self.assertEqual(listed.status_code, 200)
        tools = listed.json()["result"]["tools"]
        run_tool = next(tool for tool in tools if tool["name"] == "brain.sha256d_run_rtl")
        self.assertEqual(
            run_tool["inputSchema"]["properties"]["case"]["enum"],
            ["genesis_nonce_search", "nonce_sweep", "header_hash"],
        )

        # An unknown case must fail closed before invoking external RTL tools.
        response = self.client.post("/mcp", headers=self.headers, json={
            "jsonrpc": "2.0", "id": 11, "method": "tools/call",
            "params": {
                "name": "brain.sha256d_run_rtl",
                "arguments": {"case": "arbitrary-command", "timeout_seconds": 1.0},
            },
        })
        self.assertEqual(response.status_code, 200)
        result = response.json()["result"]["structuredContent"]
        self.assertFalse(result["ok"])
        self.assertFalse(result["external_claims_verified"])
        self.assertEqual(result["rtl_result"]["status"], "BLOCKED")
        self.assertEqual(result["rtl_result"]["error_code"], "RTL_CASE_NOT_ALLOWLISTED")

    def test_mcp_validates_shared_cpu_rtl_evidence_contract(self):
        record = make_layer_result(
            layer="cpu_reference", status="PASS",
            evidence={
                "execution_scope": "HOST_CPU_SOFTWARE_ONLY",
                "hashes_completed": 1,
                "elapsed_seconds": 0.1,
                "hashrate_hs": 10.0,
                "last_digest_hex": "a" * 64,
            },
        )
        response = self.client.post("/mcp", headers=self.headers, json={
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "brain.sha256d_validate_evidence", "arguments": {"record": record}},
        })
        self.assertEqual(response.status_code, 200)
        result = response.json()["result"]["structuredContent"]
        self.assertTrue(result["ok"])
        self.assertTrue(result["validation"]["valid"])
        self.assertFalse(result["external_claims_verified"])

        record["evidence"]["hashes_completed"] = 999
        bad = self.client.post("/mcp", headers=self.headers, json={
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {"name": "brain.sha256d_validate_evidence", "arguments": {"record": record}},
        })
        self.assertFalse(bad.json()["result"]["structuredContent"]["ok"])

    def test_mcp_layer_snapshot_keeps_pool_and_revenue_separate(self):
        response = self.client.post("/mcp", headers=self.headers, json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "brain.sha256d_layers", "arguments": {}},
        })
        self.assertEqual(response.status_code, 200)
        result = response.json()["result"]["structuredContent"]
        self.assertTrue(result["ok"])
        self.assertFalse(result["execution_started"])
        snapshot = result["sha256d_layers"]
        self.assertFalse(snapshot["pool_connected"])
        self.assertFalse(snapshot["accepted_share_verified"])
        self.assertFalse(snapshot["physical_asic_verified"])
        self.assertFalse(snapshot["revenue_verified"])
        self.assertEqual(snapshot["layers"][1]["status"], "NOT_RUN")
        self.assertTrue(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
