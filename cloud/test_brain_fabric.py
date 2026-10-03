from cloud.brain_fabric import create_job, get_job, heartbeat, register_node, snapshot, transition_job

def test_fabric_registers_and_schedules(tmp_path, monkeypatch):
    monkeypatch.setenv("BRAIN_FABRIC_STATE_DIR", str(tmp_path))
    node = register_node("brain-node-test", provider="self-hosted", architecture="arm64",
                         cpu=2, memory_mb=12288, storage_gb=100,
                         capabilities=["docker", "ffmpeg"])
    assert node["state"] == "READY"
    heartbeat("brain-node-test", jobs_running=0)
    job = create_job("film", {"title": "test"}, ["ffmpeg"])
    assert job["node_id"] == "brain-node-test"
    assert get_job(job["job_id"])["state"] == "QUEUED"
    transition_job(job["job_id"], "RUNNING", evidence={"event": "started"})
    transition_job(job["job_id"], "SUCCESS", evidence={"verified": True})
    assert get_job(job["job_id"])["state"] == "SUCCESS"
    assert snapshot()["provider_lock_in"] is False
