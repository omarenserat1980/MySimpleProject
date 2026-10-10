from brain_v12.brain.golden_mission_live_probe import _safe_base_url, probe_runtime


def test_live_probe_records_hashes_but_cannot_claim_full_closure(monkeypatch):
    responses = iter([
        (200, {"ok": True, "status": "READY"}, "a" * 64),
        (200, {"ok": True, "enabled": False, "worker": {"mode": "REMINDERS_ONLY"}}, "b" * 64),
    ])
    monkeypatch.setattr("brain_v12.brain.golden_mission_live_probe._get_json", lambda *args: next(responses))
    report = probe_runtime("http://127.0.0.1:8012", "do-not-record-this-key")
    assert report["checks"][0]["passed"] is True
    assert report["checks"][0]["response_sha256"] == "a" * 64
    assert report["checks"][1]["passed"] is True
    assert report["status"] == "BLOCKED"
    assert report["checks"][2]["name"] == "mission_persistence_restart"
    assert report["checks"][2]["passed"] is False
    assert report["checks"][3]["name"] == "restore_drill"
    assert report["checks"][3]["passed"] is False
    assert "do-not-record-this-key" not in str(report)
    assert report["safety"]["changes_service_state"] is False


def test_live_probe_blocks_unready_or_unauthenticated_runtime(monkeypatch):
    responses = iter([
        (503, {"ok": False, "status": "STARTING"}, "c" * 64),
        (401, {"detail": "Unauthorized"}, "d" * 64),
    ])
    monkeypatch.setattr("brain_v12.brain.golden_mission_live_probe._get_json", lambda *args: next(responses))
    report = probe_runtime("http://127.0.0.1:8012")
    assert report["status"] == "BLOCKED"
    assert report["checks"][0]["passed"] is False
    assert report["checks"][1]["passed"] is False


def test_live_probe_rejects_public_plain_http_and_embedded_credentials():
    import pytest
    with pytest.raises(ValueError):
        _safe_base_url("http://example.com")
    with pytest.raises(ValueError):
        _safe_base_url("http://user:password@127.0.0.1:8012")
