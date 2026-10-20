from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from brain_v12.brain.public_pool_evidence_api import create_public_pool_evidence_router


class FakeEvidenceStore:
    def __init__(self):
        self.items = []

    def append(self, task_id, kind, payload, **kwargs):
        item = {
            "evidence_id": f"evidence-{len(self.items) + 1}",
            "task_id": task_id,
            "kind": kind,
            "verification_status": "UNVERIFIED",
            "sha256": "test-digest",
            "payload": payload,
            "metadata": kwargs,
        }
        self.items.append(item)
        return item


def make_client(store):
    app = FastAPI()
    app.include_router(create_public_pool_evidence_router(store))
    return TestClient(app)


def test_record_requires_control_key(monkeypatch, tmp_path):
    monkeypatch.delenv("BRAIN_CONTROL_KEY", raising=False)
    monkeypatch.setenv("BRAIN_PUBLIC_POOL_EVIDENCE_ROOT", str(tmp_path))
    client = make_client(FakeEvidenceStore())
    response = client.post("/api/mining-node/pool-evidence/record")
    assert response.status_code == 503
    assert response.json()["detail"] == "CONTROL_PLANE_NOT_CONFIGURED"


def test_record_persists_only_unverified_local_evidence(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAIN_CONTROL_KEY", "test-only-key")
    monkeypatch.setenv("BRAIN_PUBLIC_POOL_EVIDENCE_ROOT", str(tmp_path))
    (tmp_path / "public-pool-debug.log").write_text("no accepted share record\n", encoding="utf-8")
    (tmp_path / "public-pool-latest.json").write_text(
        json.dumps({"workersCount": 0, "totalAcceptedShares": 0, "workers": []}), encoding="utf-8"
    )
    store = FakeEvidenceStore()
    client = make_client(store)
    response = client.post(
        "/api/mining-node/pool-evidence/record",
        headers={"X-Brain-Control-Key": "test-only-key"},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "UNVERIFIED_DIAGNOSTIC_PERSISTED"
    assert result["verification_status"] == "UNVERIFIED"
    assert result["network_access_performed"] is False
    assert result["miner_started_or_stopped"] is False
    assert result["pool_settings_changed"] is False
    assert result["accepted_shares_verified"] is False
    assert result["payout_verified"] is False
    assert result["revenue_verified"] is False
    assert len(store.items) == 1
    assert store.items[0]["kind"] == "public_pool_diagnostic"


def test_record_rejects_configured_path_outside_root(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAIN_CONTROL_KEY", "test-only-key")
    monkeypatch.setenv("BRAIN_PUBLIC_POOL_EVIDENCE_ROOT", str(tmp_path / "allowed"))
    monkeypatch.setenv("BRAIN_PUBLIC_POOL_MINER_LOG", str(tmp_path / "outside.log"))
    (tmp_path / "allowed").mkdir()
    (tmp_path / "outside.log").write_text("sensitive", encoding="utf-8")
    client = make_client(FakeEvidenceStore())
    response = client.post(
        "/api/mining-node/pool-evidence/record",
        headers={"X-Brain-Control-Key": "test-only-key"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "EVIDENCE_PATH_OUTSIDE_CONFIGURED_ROOT"
