import pytest
from fastapi import HTTPException

from brain_v12.brain import thin_membrane


def clear_membrane_env(monkeypatch):
    for key in (
        "BRAIN_CLOUD_HUB_URL",
        "BRAIN_DEVICE_ID",
        "BRAIN_AGENT_KEY",
        "BRAIN_AGENT_KEY_SHA256",
        "BRAIN_EMULATOR_KEY",
        "BRAIN_EMULATOR_AGENT_KEY",
        "BRAIN_AGENT_KEY_FILE",
        "V12_AGENT_KEY_FILE",
    ):
        monkeypatch.delenv(key, raising=False)


def test_unconfigured_membrane_is_not_claimed_connected(monkeypatch):
    clear_membrane_env(monkeypatch)
    result = thin_membrane.thin_membrane_status()
    assert result["ok"] is True
    assert result["state"] == "NOT_READY"
    assert result["summary"]["connection_verified"] is False
    assert result["summary"]["heartbeat_verified"] is False
    assert result["summary"]["task_roundtrip_verified"] is False
    assert result["safety"]["production_changed"] is False


def test_tls_endpoint_and_device_credentials_only_prepare_connectivity_test(monkeypatch):
    monkeypatch.setenv("BRAIN_CLOUD_HUB_URL", "https://brain.example.invalid/api")
    monkeypatch.setenv("BRAIN_DEVICE_ID", "realme-test-01")
    monkeypatch.setenv("BRAIN_AGENT_KEY", "do-not-return-this")
    result = thin_membrane.thin_membrane_status()
    assert result["state"] == "READY_FOR_CONNECTIVITY_TEST"
    assert result["cloud_endpoint"]["tls_required_satisfied"] is True
    assert result["summary"]["connection_verified"] is False
    assert "do-not-return-this" not in repr(result)
    assert "https://brain.example.invalid" not in repr(result)
    assert result["capabilities"]["cloud_contact_attempted"] is False


def test_plain_http_is_not_accepted_as_ready(monkeypatch):
    monkeypatch.setenv("BRAIN_CLOUD_HUB_URL", "http://brain.example.invalid")
    monkeypatch.setenv("BRAIN_DEVICE_ID", "realme-test-01")
    monkeypatch.setenv("BRAIN_AGENT_KEY", "placeholder")
    result = thin_membrane.thin_membrane_status()
    assert result["cloud_endpoint"]["state"] == "INSECURE_HTTP"
    assert result["state"] == "NOT_READY"


def test_connectivity_probe_fails_closed_without_token(monkeypatch):
    monkeypatch.delenv("BRAIN_MEMBRANE_PROBE_TOKEN", raising=False)
    with pytest.raises(HTTPException) as exc:
        thin_membrane.connectivity_check(None)
    assert exc.value.status_code == 503
    assert exc.value.detail == "PROBE_NOT_CONFIGURED"


def test_connectivity_probe_requires_matching_token_and_does_not_claim_cloud_connection(monkeypatch):
    monkeypatch.setenv("BRAIN_MEMBRANE_PROBE_TOKEN", "test-only-probe-secret")
    with pytest.raises(HTTPException) as exc:
        thin_membrane.connectivity_check("wrong")
    assert exc.value.status_code == 401
    assert exc.value.detail == "PROBE_AUTH_FAILED"
    response = thin_membrane.connectivity_check("test-only-probe-secret")
    assert response["device_cloud_connection_verified"] is False
    assert response["task_roundtrip_verified"] is False
    assert "test-only-probe-secret" not in repr(response)
