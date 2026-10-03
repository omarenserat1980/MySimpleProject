import importlib
import sys

from fastapi.testclient import TestClient

def test_fabric_api_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setenv("BRAIN_FABRIC_STATE_DIR", str(tmp_path / "fabric"))
    monkeypatch.setenv("BRAIN_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("BRAIN_CONTROL_TOKEN", "test-control-token")
    monkeypatch.setenv("BRAIN_API_QUEUE_WORKER", "0")

    for name in list(sys.modules):
        if name == "cloud.api_server" or name.startswith("cloud.api_server."):
            sys.modules.pop(name, None)

    api_server = importlib.import_module("cloud.api_server")
    client = TestClient(api_server.app)
    auth = {"Authorization": "Bearer test-control-token"}

    status = client.get("/v1/fabric", headers=auth)
    assert status.status_code == 200
    assert status.json()["system"] == "BRAIN_CLOUD_FABRIC"

    enrollment = client.post("/v1/fabric/enroll", headers=auth,
                             json={"node_id": "api-node", "ttl_seconds": 300})
    assert enrollment.status_code == 200
    token = enrollment.json()["enrollment_token"]

    heartbeat = client.post(
        "/v1/fabric/nodes/api-node/heartbeat",
        json={"enrollment_token": token, "state": "READY", "jobs_running": 0,
              "architecture": "x86_64", "cpu": 4, "memory_mb": 8192,
              "storage_gb": 50, "capabilities": ["python", "ffmpeg"]},
    )
    assert heartbeat.status_code == 200
    node = heartbeat.json()["node"]
    assert node["node_id"] == "api-node"
    assert node["capacity"] == {"cpu": 4.0, "memory_mb": 8192, "storage_gb": 50}
    assert node["capabilities"] == ["ffmpeg", "python"]

    nodes = client.get("/v1/fabric/nodes", headers=auth)
    assert nodes.status_code == 200
    assert nodes.json()["nodes"][0]["node_id"] == "api-node"

    job = client.post("/v1/fabric/jobs", headers=auth,
                      json={"kind": "api-integration", "payload": {"test": True},
                            "required_capabilities": ["ffmpeg"]})
    assert job.status_code == 200
    job_id = job.json()["job"]["job_id"]

    running = client.post(f"/v1/fabric/jobs/{job_id}/transition", headers=auth,
                          json={"state": "RUNNING", "evidence": {"verified": True}})
    assert running.status_code == 200

    completed = client.post(
        f"/v1/fabric/jobs/{job_id}/transition", headers=auth,
        json={"state": "SUCCESS",
              "evidence": {"stage": "master_qc", "verified": True, "artifact": "api-test"}},
    )
    assert completed.status_code == 200
    assert completed.json()["job"]["state"] == "SUCCESS"

    fetched = client.get(f"/v1/fabric/jobs/{job_id}", headers=auth)
    assert fetched.status_code == 200
    assert fetched.json()["job"]["state"] == "SUCCESS"

def test_fabric_api_rejects_bad_control_token(tmp_path, monkeypatch):
    monkeypatch.setenv("BRAIN_FABRIC_STATE_DIR", str(tmp_path / "fabric"))
    monkeypatch.setenv("BRAIN_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("BRAIN_CONTROL_TOKEN", "correct-token")
    monkeypatch.setenv("BRAIN_API_QUEUE_WORKER", "0")

    for name in list(sys.modules):
        if name == "cloud.api_server" or name.startswith("cloud.api_server."):
            sys.modules.pop(name, None)

    api_server = importlib.import_module("cloud.api_server")
    client = TestClient(api_server.app)
    response = client.get("/v1/fabric", headers={"Authorization": "Bearer wrong-token"})
    assert response.status_code == 401
