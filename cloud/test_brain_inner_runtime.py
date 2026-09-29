from cloud.runtime_orchestrator import CloudRuntime

def test_runtime_has_combined_inner_state():
    runtime = CloudRuntime()
    snapshot = runtime.snapshot()
    assert "inner_state" in snapshot
    assert snapshot["inner_state"]["literal_human_inner_state_claim"] is False

def test_runtime_heart_nafs_review_blocks_high_harm():
    runtime = CloudRuntime()
    result = runtime._inner_preflight(
        "dangerous-runtime-action",
        {
            "heart_evidence": 0.2,
            "heart_ambiguity": 0.9,
            "heart_pressure": 0.8,
            "heart_social_impact": 0.0,
            "nafs_benefit": 0.1,
            "nafs_harm": 0.95,
            "nafs_temptation": 0.9,
            "nafs_uncertainty": 0.9,
            "nafs_reversible": False,
        },
    )
    assert result["decision"] == "REVIEW"
    assert result["nafs"]["decision"] == "REJECT"
