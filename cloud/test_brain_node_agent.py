from cloud.brain_node_agent import node_identity, run_forever

def test_node_identity_has_resources(monkeypatch):
    monkeypatch.setenv("BRAIN_NODE_ID", "test-node")
    monkeypatch.setenv("BRAIN_NODE_CAPABILITIES", "python,ffmpeg,python")
    node = node_identity()
    assert node["node_id"] == "test-node"
    assert node["cpu"] >= 1
    assert node["memory_mb"] >= 0
    assert node["storage_gb"] >= 0
    assert node["capabilities"] == ["ffmpeg", "python"]

def test_run_forever_sends_periodic_heartbeats_without_execution():
    calls = []
    sleeps = []
    def sender(url, token):
        calls.append((url, token))
        if len(calls) >= 2:
            return {"ok": True}
        return {"ok": True}
    def fake_sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) >= 1:
            raise KeyboardInterrupt
    try:
        run_forever("https://brain.example", "secret", 5, sender=sender, sleep=fake_sleep)
    except KeyboardInterrupt:
        pass
    assert calls == [
        ("https://brain.example", "secret"),
        ("https://brain.example", "secret"),
    ]
    assert sleeps == [5.0]
