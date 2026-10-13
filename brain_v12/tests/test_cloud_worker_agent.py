"""Focused tests for software-only cloud worker heartbeat behavior."""
import json
import httpx

from brain_v12 import cloud_worker_agent as agent


def client_for(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_origin_requires_https():
    assert agent._https_origin("https://brain.example")
    assert not agent._https_origin("http://brain.example")
    assert not agent._https_origin("https://user:pass@brain.example")


def test_preflight_rejects_device_adapter_mode():
    def handler(request):
        if request.url.path == "/health":
            return httpx.Response(200, json={"ok": True, "deployment": {"converged": True}})
        return httpx.Response(200, json={"mode": "software-only", "device_adapters_enabled": True})
    result = agent.preflight(client_for(handler), "https://brain.example")
    assert result["verified"] is False


def test_registers_before_heartbeat(tmp_path, monkeypatch):
    monkeypatch.setattr(agent, "ROOT", tmp_path)
    monkeypatch.setattr(agent, "HEARTBEAT", tmp_path / "cloud-worker-heartbeat.json")
    def handler(request):
        if request.url.path == "/health":
            return httpx.Response(200, json={"ok": True, "deployment": {"converged": True}})
        if request.url.path == "/api/brain/workers":
            return httpx.Response(200, json={"mode": "software-only", "device_adapters_enabled": False})
        if request.url.path == "/api/brain/workers/register":
            data = json.loads(request.content)
            assert data["kind"] == "software"
            return httpx.Response(200, json={"ok": True, "mode": "software-only"})
        return httpx.Response(404)
    result = agent.tick(client_for(handler), "https://brain.example")
    assert result["ok"] is True
    payload = json.loads(agent.HEARTBEAT.read_text(encoding="utf-8"))
    assert payload["state"] == "RUNNING"
    assert payload["preflight"]["verified"] is True


def test_failed_preflight_clears_stale_heartbeat(tmp_path, monkeypatch):
    monkeypatch.setattr(agent, "ROOT", tmp_path)
    monkeypatch.setattr(agent, "HEARTBEAT", tmp_path / "cloud-worker-heartbeat.json")
    agent.HEARTBEAT.write_text('{"state":"RUNNING"}', encoding="utf-8")
    def handler(request):
        return httpx.Response(503, json={"ok": False})
    result = agent.tick(client_for(handler), "https://brain.example")
    assert result["ok"] is False
    assert not agent.HEARTBEAT.exists()
