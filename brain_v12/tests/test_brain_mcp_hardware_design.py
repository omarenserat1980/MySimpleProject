import asyncio
import json

from starlette.requests import Request

from brain_v12.brain.brain_mcp import PROTOCOL_VERSION, build_mcp_router


class _BrainAI:
    def status(self):
        return {"status": "test"}


class _DeviceBridge:
    def agent_status(self):
        return {"agents": []}


class _Store:
    pass


def _rpc(method, params=None, request_id=1):
    router = build_mcp_router(_BrainAI(), _DeviceBridge(), _Store())
    endpoint = next(
        route.endpoint
        for route in router.routes
        if route.path == "/mcp" and "POST" in route.methods
    )
    body = json.dumps({
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params or {},
    }).encode("utf-8")
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/mcp",
        "raw_path": b"/mcp",
        "query_string": b"",
        "root_path": "",
        "headers": [
            (b"mcp-protocol-version", PROTOCOL_VERSION.encode("ascii")),
            (b"content-type", b"application/json"),
        ],
        "server": ("testserver", 80),
        "client": ("testclient", 12345),
    }

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    request = Request(scope, receive)
    response = asyncio.run(endpoint(request))
    return json.loads(response.body.decode("utf-8"))


def test_mcp_lists_hardware_design_tool_and_returns_generated_rtl():
    listed = _rpc("tools/list")["result"]["tools"]
    tool = next(item for item in listed if item["name"] == "brain.hardware_design")
    assert "SystemVerilog" in tool["description"]

    response = _rpc(
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
    )["result"]

    assert response["isError"] is False
    result = response["structuredContent"]
    assert result["status"] == "DESIGN_GENERATED"
    assert "assign sum_node = a + b;" in result["rtl"]
    assert result["verification"]["rtl_simulation"] == "NOT_RUN"
    assert result["verification"]["physical_hardware"] == "NOT_VERIFIED"


def test_mcp_hardware_design_tool_rejects_invalid_graph_and_never_claims_success():
    response = _rpc(
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
    )["result"]

    assert response["isError"] is True
    assert response["structuredContent"]["status"] == "INVALID_HARDWARE_GRAPH"
    assert response["structuredContent"]["error"].startswith("UNKNOWN_OR_FORWARD_REFERENCE")
