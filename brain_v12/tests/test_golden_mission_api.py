import tempfile
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from brain_v12.brain.golden_mission import GoldenMissionController
from brain_v12.golden_mission_api import router


class Evidence:
    def get(self, evidence_id):
        return None

    def verify_hash(self, evidence_id):
        return {"ok": False}


def make_client(tmp_path):
    controller = GoldenMissionController(
        str(Path(tmp_path) / "missions.sqlite3"),
        notifier=lambda mission, message: {"sent": False, "reason": "test"},
        evidence_store=Evidence(),
    )
    app = FastAPI()
    app.include_router(router(controller))
    return TestClient(app)


def test_create_start_and_permission_gate(tmp_path):
    client = make_client(tmp_path)
    created = client.post("/api/golden-missions", json={
        "title": "VM boot check",
        "objective": "Prove the test VM boots",
        "acceptance": ["guest boots", "health endpoint responds"],
        "estimate_minutes": 25,
        "update_minutes": 5,
    })
    assert created.status_code == 200
    mission = created.json()["mission"]
    mission_id = mission["mission_id"]
    assert mission["status"] == "PLANNED"
    assert mission["due_at"]
    assert mission["next_update_at"]

    blocked = client.post(f"/api/golden-missions/{mission_id}/permission-required", json={
        "permission": "hyperv_admin",
        "detail": "Explicit owner approval needed",
    })
    assert blocked.status_code == 200
    assert blocked.json()["mission"]["status"] == "WAITING_PERMISSION"

    wrong = client.post(f"/api/golden-missions/{mission_id}/permission-grant", json={
        "permission": "root",
        "approved_by": "owner",
    })
    assert wrong.status_code == 409
    assert wrong.json()["detail"] == "PERMISSION_MISMATCH"

    granted = client.post(f"/api/golden-missions/{mission_id}/permission-grant", json={
        "permission": "hyperv_admin",
        "approved_by": "owner",
    })
    assert granted.status_code == 200
    assert granted.json()["mission"]["status"] == "RUNNING"


def test_close_endpoint_cannot_trust_client_boolean(tmp_path):
    client = make_client(tmp_path)
    created = client.post("/api/golden-missions", json={
        "title": "Close gate",
        "objective": "Do not accept unverified completion",
        "acceptance": ["evidence exists"],
    })
    mission_id = created.json()["mission"]["mission_id"]
    assert client.post(f"/api/golden-missions/{mission_id}/start").status_code == 200
    # Endpoint accepts only evidence identifiers/hashes, never caller-supplied verified=true flags.
    response = client.post(f"/api/golden-missions/{mission_id}/close", json={
        "evidence_id": "fake",
        "evidence_sha256": "0" * 64,
        "summary": "force close",
    })
    assert response.status_code == 409
    assert response.json()["detail"] == "MISSION_EVIDENCE_NOT_FOUND_OR_MISMATCHED"


def test_due_endpoint_returns_persistent_due_items(tmp_path):
    client = make_client(tmp_path)
    response = client.get("/api/golden-missions/due")
    assert response.status_code == 200
    assert response.json()["ok"] is True
