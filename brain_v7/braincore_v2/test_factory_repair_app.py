from .factory_repair_app import diagnose, repair, repair_100_cycles, FAL_DEFAULT

def test_repair_resolves_empty_model(monkeypatch, tmp_path):
    monkeypatch.delenv("FAL_MODEL", raising=False)
    monkeypatch.setenv("FACTORY_ALLOW_LOCAL_FALLBACK", "1")
    monkeypatch.setenv("FACTORY_LAST_ERROR", "User is locked: exhausted balance")
    monkeypatch.setenv("FFMPEG_BIN", "ffmpeg")
    result = repair("User is locked: exhausted balance", str(tmp_path / "repair.json"))
    assert result["diagnosis"]["fal_model"] == FAL_DEFAULT
    assert result["diagnosis"]["fal_quota_blocked"] is True
    assert "resolved_empty_FAL_MODEL_to_known_default" in result["actions"]

def test_diagnose_never_claims_provider_success(monkeypatch):
    monkeypatch.setenv("FAL_KEY", "x")
    d = diagnose("HTTP 403 User is locked: exhausted balance")
    assert d["fal_quota_blocked"] is True
    assert d["recommended_route"] in {"local_ffmpeg_cinematic", "fal", "configuration_required"}

def test_100_cycle_controller_stops_on_healthy_runtime(monkeypatch, tmp_path):
    monkeypatch.setenv("FACTORY_ALLOW_LOCAL_FALLBACK", "1")
    monkeypatch.setenv("FAL_MODEL", "")
    monkeypatch.setenv("FFMPEG_BIN", "ffmpeg")
    result = repair_100_cycles("", str(tmp_path / "100.json"))
    assert result["cycles_completed"] <= 100
    assert result["status"] in {"RUNTIME_HEALTHY", "REPAIR_LIMIT_REACHED"}
    assert len(result["history"]) == result["cycles_completed"]
