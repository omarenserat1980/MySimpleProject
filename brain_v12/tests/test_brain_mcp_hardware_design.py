from fastapi import FastAPI
from fastapi.testclient import TestClient

from brain_v12.brain.brain_mcp import PROTOCOL_VERSION, build_mcp_router


class _BrainAI:
    def status(self):
        return {"status": "test"}


class _DeviceBridge:
    def agent_status(self):
        return {"agents": []}


class _Store:
    pass


def _client():
    app = FastAPI()
    app.include_router(build_mcp_router(_BrainAI(), _DeviceBridge(), _Store()))
    return TestClient(app)


def _rpc(client, method, params=None, request_id=1):
    return client.post(
        "/mcp",
        headers={"MCP-Protocol-Version": PROTOCOL_VERSION},
        json={"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}},
    )


def test_mcp_lists_hardware_design_tool_and_returns_generated_rtl():
    client = _client()
    listed = _rpc(client, "tools/list").json()["result"]["tools"]
    tool = next(item for item in listed if item["name"] == "brain.hardware_design")
    assert "SystemVerilog" in tool["description"]

    response = _rpc(
        client,
        "tools/call",
        {
            "name": "brain.hardware_design",
            "arguments": {
                "module": "brain_adder",
                "width": 8,
                "inputs": ["a", "b"],
                "nodes": [{"id": "sum_node", "op": "add", "inputs": ["a", "b"]}],
                "outputs": {"result": "sum_node"},
            },
        },
    ).json()["result"]

    assert response["isError"] is False
    result = response["structuredContent"]
    assert result["status"] == "DESIGN_GENERATED"
    assert "assign sum_node = a + b;" in result["rtl"]
    assert result["verification"]["rtl_simulation"] == "NOT_RUN"
    assert result["verification"]["physical_hardware"] == "NOT_VERIFIED"


def test_mcp_hardware_design_tool_rejects_invalid_graph_and_never_claims_success():
    client = _client()
    response = _rpc(
        client,
        "tools/call",
        {
            "name": "brain.hardware_design",
            "arguments": {
                "module": "bad",
                "width": 8,
                "inputs": ["a"],
                "nodes": [{"id": "x", "op": "add", "inputs": ["a", "missing"]}],
                "outputs": {"result": "x"},
            },
        },
    ).json()["result"]

    assert response["isError"] is True
    assert response["structuredContent"]["status"] == "INVALID_HARDWARE_GRAPH"
    assert response["structuredContent"]["error"].startswith("UNKNOWN_OR_FORWARD_REFERENCE")
