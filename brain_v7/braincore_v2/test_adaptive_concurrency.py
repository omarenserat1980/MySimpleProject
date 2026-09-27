from brain_v7.braincore_v2.speed_optimizer import speed_policy

def test_adaptive_concurrency_stays_within_ceiling(tmp_path, monkeypatch):
    path = tmp_path / "throughput.json"
    import json
    path.write_text(json.dumps({"version": 1, "stages": {"generation": {
        "steady_samples": 4, "ewma_steady_latency_s": 5.0}}, "updated_at": 0}), encoding="utf-8")
    monkeypatch.setenv("FACTORY_THROUGHPUT_PATH", str(path))
    monkeypatch.setenv("FACTORY_RENDER_CONCURRENCY", "3")
    monkeypatch.setenv("FACTORY_MAX_CONCURRENCY", "4")
    monkeypatch.setenv("FACTORY_ADAPTIVE_CONCURRENCY", "1")
    assert speed_policy()["concurrency"] == 4

def test_adaptive_concurrency_does_not_bypass_ceiling(tmp_path, monkeypatch):
    path = tmp_path / "throughput.json"
    import json
    path.write_text(json.dumps({"version": 1, "stages": {"generation": {
        "steady_samples": 4, "ewma_steady_latency_s": 5.0}}, "updated_at": 0}), encoding="utf-8")
    monkeypatch.setenv("FACTORY_THROUGHPUT_PATH", str(path))
    monkeypatch.setenv("FACTORY_RENDER_CONCURRENCY", "8")
    monkeypatch.setenv("FACTORY_MAX_CONCURRENCY", "2")
    monkeypatch.setenv("FACTORY_ADAPTIVE_CONCURRENCY", "1")
    assert speed_policy()["concurrency"] == 2
