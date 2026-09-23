from brain_v7.braincore_v2.worker_health import WorkerHealthRegistry


def test_health_marks_fresh_worker_live():
    registry = WorkerHealthRegistry(stale_after_s=60)
    registry.beat("brain-v7-core", cycle=3)
    report = registry.inspect(now=registry._heartbeats["brain-v7-core"].timestamp + 10)
    assert report["live_workers"] == 1


def test_health_marks_stale_worker_not_live():
    registry = WorkerHealthRegistry(stale_after_s=60)
    registry.beat("brain-v7-core", cycle=3)
    report = registry.inspect(now=registry._heartbeats["brain-v7-core"].timestamp + 61)
    assert report["live_workers"] == 0
