from fastapi import FastAPI
from fastapi.testclient import TestClient

from brain_v12.brain.brain_mcp import PROTOCOL_VERSION, build_mcp_router


class FakeBrainAI:
    def status(self):
        return {"configured": True}


class FakeDeviceBridge:
    def agent_status(self):
        return {"agents": []}


class FakeStore:
    pass


def make_client():
    app = FastAPI()
    app.include_router(
        build_mcp_router(FakeBrainAI(), FakeDeviceBridge(), FakeStore())
    )
    return TestClient(app)


def test_initialize_accepts_missing_protocol_header_and_negotiates_version():
    client = make_client()
    response = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "contract-test", "version": "1"},
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["result"]["protocolVersion"] == PROTOCOL_VERSION
    assert payload["result"]["serverInfo"]["name"] == "Electronic Brain"


def test_tools_list_requires_supported_protocol_header_after_initialize():
    client = make_client()
    response = client.post(
        "/mcp",
        headers={"MCP-Protocol-Version": PROTOCOL_VERSION},
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    )

    assert response.status_code == 200
    assert {tool["name"] for tool in response.json()["result"]["tools"]} == {
        "brain.chat",
        "brain.device_status",
        "brain.evidence",
        "brain.status",
    }


def test_post_without_header_is_rejected_after_initialize_method():
    client = make_client()
    response = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 3, "method": "tools/list"},
    )

    assert response.status_code == 400
    assert response.json()["error"] == "UNSUPPORTED_MCP_PROTOCOL_VERSION"
