"""Contract tests for the existing stateless MCP router using an in-process ASGI client."""
import json
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from brain_v12.brain.asic_resource_adapter import ASICResourceAdapter
from brain_v12.brain.brain_mcp import PROTOCOL_VERSION, build_mcp_router


class FakeBrainAI:
    def status(self):
        return {"state": "TEST_ONLY"}

    def chat(self, message, approved=False):
        return SimpleNamespace(
            ok=True, mode="TEST_ONLY", reply=message, model="fixture",
            tool_calls=[], evidence=[], error=None,
        )


class FakeDeviceBridge:
    def agent_status(self):
        return {"connected": False, "evidence": "TEST_FIXTURE"}


def client(asic_resources=None):
    app = FastAPI()
    app.include_router(build_mcp_router(
        FakeBrainAI(), FakeDeviceBridge(), object(), asic_resources=asic_resources
    ))
    return TestClient(app)


def rpc(test_client, method, params=None, request_id=1):
    return test_client.post(
        "/mcp",
        headers={"MCP-Protocol-Version": PROTOCOL_VERSION},
        json={"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}},
    )


def test_mcp_initialize_and_tools_list_contract():
    c = client()
    initialized = rpc(c, "initialize", {"protocolVersion": PROTOCOL_VERSION})
    assert initialized.status_code == 200
    assert initialized.json()["result"]["protocolVersion"] == PROTOCOL_VERSION

    listed = rpc(c, "tools/list")
    assert listed.status_code == 200
    names = {tool["name"] for tool in listed.json()["result"]["tools"]}
    assert {"brain.status", "brain.device_status", "brain.evidence", "brain.chat"} <= names


def test_mcp_tool_call_returns_structured_result_without_claiming_live_worker():
    c = client()
    response = rpc(c, "tools/call", {"name": "brain.device_status", "arguments": {}})
    assert response.status_code == 200
    result = response.json()["result"]["structuredContent"]
    assert result["ok"] is True
    assert result["device"]["connected"] is False
    assert result["device"]["evidence"] == "TEST_FIXTURE"
    assert response.json()["result"]["isError"] is False


def test_mcp_rejects_unsupported_protocol_version():
    response = client().post(
        "/mcp",
        headers={"MCP-Protocol-Version": "unsupported-version"},
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "UNSUPPORTED_MCP_PROTOCOL_VERSION"


def test_mcp_rejects_unknown_tool():
    response = rpc(client(), "tools/call", {"name": "brain.fake", "arguments": {}})
    assert response.status_code == 200
    assert response.json()["error"]["code"] == -32602



def test_mcp_asic_sha256d_tool_runs_bounded_software_work_and_preserves_evidence_boundary():
    adapter = ASICResourceAdapter()
    c = client(asic_resources=adapter)
    listed = rpc(c, "tools/list")
    names = {tool["name"] for tool in listed.json()["result"]["tools"]}
    assert "brain.asic_sha256d_simulate" in names

    response = rpc(c, "tools/call", {
        "name": "brain.asic_sha256d_simulate",
        "arguments": {
            "header_hex": "00" * 80,
            "target_hex": "f" * 64,
            "start_nonce": 9,
            "max_attempts": 1,
        },
    })
    assert response.status_code == 200
    result = response.json()["result"]["structuredContent"]
    assert result["ok"] is True
    assert result["status"] == "SIMULATION_ONLY"
    assert result["result"]["result"]["found"] is True
    assert result["result"]["result"]["nonce"] == 9
    assert result["result"]["rtl_executed"] is False
    assert result["result"]["physical_asic_executed"] is False
    assert result["result"]["pool_contacted"] is False
    assert result["result"]["share_submitted"] is False
    assert result["result"]["revenue_verified"] is False
