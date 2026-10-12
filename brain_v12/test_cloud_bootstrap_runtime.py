from __future__ import annotations

import json

from brain_v12 import cloud_bootstrap


class _Response:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class _Client:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url):
        assert url.endswith("/health")
        return _Response(self.payload)


def test_verify_runtime_requires_worker_attestation(monkeypatch):
    monkeypatch.setattr(
        cloud_bootstrap.httpx,
        "Client",
        lambda **kwargs: _Client(
            {
                "ok": True,
                "status": "healthy",
                "runtime": "BRAIN_CLOUD_NATIVE",
                "state": "NOT_RUNNING",
            }
        ),
    )
    result = cloud_bootstrap.verify_runtime("https://brain.example.com")
    assert result["ok"] is False
    assert result["state"] == "RUNTIME_NOT_VERIFIED"


def test_verify_runtime_accepts_actual_running_worker(monkeypatch):
    monkeypatch.setattr(
        cloud_bootstrap.httpx,
        "Client",
        lambda **kwargs: _Client(
            {
                "ok": True,
                "status": "healthy",
                "runtime": "BRAIN_CLOUD_NATIVE",
                "state": "RUNNING",
                "worker": {"verified": True},
            }
        ),
    )
    result = cloud_bootstrap.verify_runtime("https://brain.example.com")
    assert result["ok"] is True
    assert result["state"] == "VERIFIED_RUNNING"
