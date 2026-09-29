from cloud.runtime_orchestrator import CloudRuntime


def test_runtime_is_cloud_only():
    rt = CloudRuntime()
    snap = rt.snapshot()
    assert snap["runtime"] == "brain_cloud"
    assert snap["device_required"] is False
    assert snap["termux_required"] is False
    assert "storage" in snap
    assert "queue" in snap


def test_queue_round_trip():
    rt = CloudRuntime()
    job = rt.enqueue("test", {"title": "cloud-test"})
    found = rt.get(job["id"])
    assert found is not None
    assert found["stage"] == "queued"
    assert found["payload"]["title"] == "cloud-test"


def test_cinematic_jobs_use_verified_production_contract():
    rt = CloudRuntime()
    job = rt.enqueue("cinematic", {"title": "contract-test"})
    assert job["payload"]["route"] == "cloud_runtime_reliability_engine"
    assert job["payload"]["production_contract"] == "verified_mp4_v1"


def test_queued_job_is_atomically_claimed_before_processing():
    rt = CloudRuntime()
    job = rt.enqueue("test", {"title": "claim-test"})
    claimed = rt.process_one()
    found = rt.get(job["id"])
    assert found is not None
    assert found["stage"] == "failed"
    assert claimed is not None
