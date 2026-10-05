import json
from datetime import datetime, timezone
from pathlib import Path

from brain_v12.local_worker import local_health_gate


def setup_tree(tmp_path):
    base = tmp_path / "local_worker"
    for name in ("queued", "running", "completed", "failed"):
        (base / name).mkdir(parents=True)
    (base / "supervisor.json").write_text(json.dumps({
        "status": "READY",
        "heartbeat_at": datetime.now(timezone.utc).isoformat(),
    }), encoding="utf-8")
    return base


def test_health_gate_ready(tmp_path, monkeypatch, capsys):
    base = setup_tree(tmp_path)
    evidence = tmp_path / "brain_local_verification.json"
    evidence.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(local_health_gate, "BASE", base)
    monkeypatch.setattr(local_health_gate, "SUPERVISOR", base / "supervisor.json")
    monkeypatch.setattr(local_health_gate, "QUEUED", base / "queued")
    monkeypatch.setattr(local_health_gate, "RUNNING", base / "running")
    monkeypatch.setattr(local_health_gate, "COMPLETED", base / "completed")
    monkeypatch.setattr(local_health_gate, "FAILED", base / "failed")
    monkeypatch.setattr(local_health_gate, "EVIDENCE", evidence)

    assert local_health_gate.main() == 0
    report = json.loads((base / "health_gate.json").read_text())
    assert report["status"] == "READY"


def test_health_gate_degraded_without_supervisor(tmp_path, monkeypatch):
    base = tmp_path / "local_worker"
    for name in ("queued", "running", "completed", "failed"):
        (base / name).mkdir(parents=True)
    evidence = tmp_path / "brain_local_verification.json"
    evidence.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(local_health_gate, "BASE", base)
    monkeypatch.setattr(local_health_gate, "SUPERVISOR", base / "supervisor.json")
    monkeypatch.setattr(local_health_gate, "QUEUED", base / "queued")
    monkeypatch.setattr(local_health_gate, "RUNNING", base / "running")
    monkeypatch.setattr(local_health_gate, "COMPLETED", base / "completed")
    monkeypatch.setattr(local_health_gate, "FAILED", base / "failed")
    monkeypatch.setattr(local_health_gate, "EVIDENCE", evidence)

    assert local_health_gate.main() == 1
    report = json.loads((base / "health_gate.json").read_text())
    assert report["status"] == "DEGRADED"
