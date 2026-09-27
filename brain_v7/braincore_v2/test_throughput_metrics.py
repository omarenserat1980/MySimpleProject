from brain_v7.braincore_v2.throughput_metrics import load, record, snapshot

def test_records_warmup_and_steady_state(tmp_path):
    path = tmp_path / "throughput.json"
    record("generation", 2.0, warmup=True, path=path)
    record("generation", 1.0, path=path)
    data = load(path)
    item = data["stages"]["generation"]
    assert item["warmup_samples"] == 1
    assert item["steady_samples"] == 1
    assert item["ewma_steady_latency_s"] == 1.0

def test_corrupt_telemetry_is_non_blocking(tmp_path):
    path = tmp_path / "throughput.json"
    path.write_text("{broken", encoding="utf-8")
    assert snapshot(path)["stages"] == {}
