"""Focused tests for the browser Chat Simulator heartbeat endpoint."""
import pytest
from fastapi import HTTPException

from brain_v12.app import brain_chat_simulator_heartbeat, _simulator_heartbeats


def test_simulator_heartbeat_acknowledges_browser_liveness():
    client_id = "test-simulator-heartbeat"
    result = brain_chat_simulator_heartbeat({"client_id": client_id, "source": "test"})

    assert result["ok"] is True
    assert result["state"] == "RUNNING"
    assert result["verified"] is True
    assert result["scope"] == "browser_simulator_only"
    assert result["timestamp"] > 0
    assert _simulator_heartbeats[client_id] == result["timestamp"]


@pytest.mark.parametrize("body", [{}, {"client_id": ""}, {"client_id": "x" * 101}])
def test_simulator_heartbeat_rejects_invalid_client_id(body):
    with pytest.raises(HTTPException) as error:
        brain_chat_simulator_heartbeat(body)
    assert error.value.status_code == 400
    assert error.value.detail == "SIMULATOR_CLIENT_ID_REQUIRED"
