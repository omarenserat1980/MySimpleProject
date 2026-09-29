from cloud.runtime_orchestrator import CloudRuntime

def test_runtime_exposes_nafs_review():
    runtime = CloudRuntime()
    snapshot = runtime.snapshot()
    assert "nafs" in snapshot
    assert snapshot["nafs"]["human_soul_claim"] is False

def test_runtime_nafs_preflight_blocks_high_harm():
    runtime = CloudRuntime()
    result = runtime._nafs_preflight(
        "test-high-harm",
        {"nafs_benefit": 0.1, "nafs_harm": 0.95, "nafs_temptation": 0.8,
         "nafs_uncertainty": 0.2, "nafs_reversible": False},
    )
    assert result["decision"] == "REJECT"
