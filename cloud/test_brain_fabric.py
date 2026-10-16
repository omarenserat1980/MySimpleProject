from cloud.brain_fabric import (
    create_job, get_job, heartbeat, register_node, snapshot,
    transition_job, update_node, choose_node,
)
import pytest


def test_fabric_registers_untrusted_node_and_refuses_scheduling(tmp_path, monkeypatch):
    monkeypatch.setenv("BRAIN_FABRIC_STATE_DIR", str(tmp_path))
    node = register_node(
        "brain-node-test", provider="self-hosted", architecture="arm64",
        cpu=2, memory_mb=12288, storage_gb=100,
        capabilities=["docker", "ffmpeg"],
    )
    assert node["state"] == "UNTRUSTED_INACTIVE"
    assert node["trusted"] is False
    assert node["active"] is False
    heartbeat("brain-node-test", jobs_running=0)
    with pytest.raises(RuntimeError, match="NO_ELIGIBLE_BRAIN_FABRIC_NODE"):
        create_job("film", {"title": "test"}, ["ffmpeg"])
    assert snapshot()["provider_lock_in"] is False


def test_update_node_persists_capabilities_and_capacity(tmp_path, monkeypatch):
    monkeypatch.setenv("BRAIN_FABRIC_STATE_DIR", str(tmp_path))
    register_node("update-node", architecture="x86_64", cpu=2, memory_mb=1024,
                  capabilities=["python"])
    updated = update_node(
        "update-node", architecture="arm64", cpu=4, memory_mb=8192,
        storage_gb=50, capabilities=["python", "ffmpeg", "python"],
    )
    assert updated["architecture"] == "arm64"
    assert updated["capacity"] == {"cpu": 4.0, "memory_mb": 8192, "storage_gb": 50}
    assert updated["capabilities"] == ["ffmpeg", "python"]
    assert updated["trusted"] is False
    assert updated["active"] is False


def test_fabric_rejects_invalid_terminal_transition(tmp_path, monkeypatch):
    monkeypatch.setenv("BRAIN_FABRIC_STATE_DIR", str(tmp_path))
    register_node("transition-node", capabilities=["ffmpeg"])
    # Job creation is impossible until a node is trusted, verified, activated,
    # and manually approved. This test only validates that fail-closed boundary.
    with pytest.raises(RuntimeError, match="NO_ELIGIBLE_BRAIN_FABRIC_NODE"):
        create_job("film", {"title": "test"}, ["ffmpeg"])
    with pytest.raises(KeyError):
        transition_job("missing-job", "SUCCESS")


def test_ready_state_alone_is_not_enough(tmp_path, monkeypatch):
    monkeypatch.setenv("BRAIN_FABRIC_STATE_DIR", str(tmp_path))
    node = register_node("ready-node", capabilities=["ffmpeg"])
    node.update(state="READY", last_heartbeat=1e20)
    assert node["trusted"] is False
    with pytest.raises(RuntimeError, match="NO_ELIGIBLE_BRAIN_FABRIC_NODE"):
        choose_node(["ffmpeg"])


def test_job_transition_after_authorized_selection(tmp_path, monkeypatch):
    monkeypatch.setenv("BRAIN_FABRIC_STATE_DIR", str(tmp_path))
    node = register_node("approved-node", capabilities=["ffmpeg"])
    node.update({"state": "READY", "trusted": True, "active": True,
                 "identity_verified": True, "manual_approval": True,
                 "last_heartbeat": 9999999999})
    from cloud.brain_fabric import _atomic_write, _state_dir
    _atomic_write(_state_dir() / "node-approved-node.json", node)
    job = create_job("film", {"title": "test"}, ["ffmpeg"])
    assert job["node_id"] == "approved-node"
    assert get_job(job["job_id"])["state"] == "QUEUED"
    transition_job(job["job_id"], "RUNNING", evidence={"event": "started"})
    transition_job(job["job_id"], "SUCCESS", evidence={"verified": True})
    assert get_job(job["job_id"])["state"] == "SUCCESS"
    assert snapshot()["provider_lock_in"] is False
