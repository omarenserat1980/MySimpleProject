from brain_v7.braincore_v2.speed_optimizer import apply_speed_policy, speed_policy

def test_ltx_fast_profile(monkeypatch):
    monkeypatch.setenv("FACTORY_SPEED_MODE", "max")
    shot = {"shot_id": "SC01-S01", "model_family": "ltx", "generation": {"generation_mode": "t2v_or_i2v"}}
    out = apply_speed_policy(shot)
    assert out["generation"]["inference_profile"] == "distilled"
    assert out["generation"]["sampling_steps"] == 8
    assert out["generation"]["quantization"] == "fp8"

def test_wan_lightning_profile(monkeypatch):
    monkeypatch.setenv("FACTORY_SPEED_MODE", "max")
    shot = {"shot_id": "SC02-S02", "model_family": "wan", "generation": {}}
    out = apply_speed_policy(shot)
    assert out["generation"]["inference_profile"] == "lightning"
    assert out["generation"]["sampling_steps"] == 4

def test_concurrency_is_bounded(monkeypatch):
    monkeypatch.setenv("FACTORY_RENDER_CONCURRENCY", "99")
    monkeypatch.setenv("FACTORY_MAX_CONCURRENCY", "8")
    assert speed_policy()["concurrency"] == 8
