import json
from pathlib import Path

from cloud.brain_fabric import (
    register_node, heartbeat, choose_node, create_job, get_job, transition_job
)
from cloud.brain_node_security import create_enrollment, verify_enrollment, consume_enrollment

def test_full_fabric_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("BRAIN_FABRIC_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("BRAIN_FABRIC_HEARTBEAT_TIMEOUT", "120")

    issued = create_enrollment("integration-node", ttl_seconds=300)
    assert verify_enrollment("integration-node", issued["enrollment_token"])

    node = register_node(
        "integration-node",
        architecture="x86_64",
        cpu=4,
        memory_mb=8192,
        storage_gb=100,
        capabilities=["docker", "ffmpeg", "python"],
    )
    assert node["state"] == "UNTRUSTED_INACTIVE"
    assert node["trusted"] is False
    assert node["active"] is False

    assert consume_enrollment("integration-node", issued["enrollment_token"])
    assert not verify_enrollment("integration-node", issued["enrollment_token"])

    live = heartbeat("integration-node", jobs_running=0)
    assert live["last_heartbeat"] > 0

    # Enrollment proves possession of a short-lived token, not device identity.
    # Scheduling must remain blocked until independent verification and manual approval.
    try:
        choose_node(["ffmpeg"])
    except RuntimeError as exc:
        assert str(exc) == "NO_ELIGIBLE_BRAIN_FABRIC_NODE"
    else:
        raise AssertionError("untrusted node was scheduled")

    from cloud.brain_fabric import _atomic_write, _state_dir
    node.update({"state": "READY", "trusted": True, "active": True,
                 "identity_verified": True, "manual_approval": True,
                 "last_heartbeat": 9999999999})
    _atomic_write(_state_dir() / "node-integration-node.json", node)
    selected = choose_node(["ffmpeg"])
    assert selected["node_id"] == "integration-node"

    job = create_job(
        "cinematic_render",
        {"title": "Brain Integration Test"},
        ["ffmpeg"],
    )
    assert job["node_id"] == "integration-node"
    assert job["state"] == "QUEUED"

    running = transition_job(job["job_id"], "RUNNING", evidence={
        "stage": "executor_started",
        "verified": True,
    })
    assert running["state"] == "RUNNING"

    completed = transition_job(job["job_id"], "SUCCESS", evidence={
        "stage": "master_qc",
        "verified": True,
        "artifact": "integration-test.mp4",
    })
    assert completed["state"] == "SUCCESS"
    assert completed["evidence"][-1]["verified"] is True
    assert get_job(job["job_id"])["state"] == "SUCCESS"


def test_scheduler_refuses_missing_capability(tmp_path, monkeypatch):
    monkeypatch.setenv("BRAIN_FABRIC_STATE_DIR", str(tmp_path))
    register_node("limited-node", capabilities=["python"])
    try:
        choose_node(["gpu"])
    except RuntimeError as exc:
        assert str(exc) == "NO_ELIGIBLE_BRAIN_FABRIC_NODE"
    else:
        raise AssertionError("scheduler accepted an ineligible node")
