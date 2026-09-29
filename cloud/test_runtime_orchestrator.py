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
