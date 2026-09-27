from brain_v7.braincore_v2.production_speed_optimizer import speed_plan, speculative_budget

def test_speed_plan_groups_compatible_shots():
    plan = speed_plan([
        {"shot_id": "A", "model_family": "ltx", "duration_s": 5},
        {"shot_id": "B", "model_family": "ltx", "duration_s": 5},
        {"shot_id": "C", "model_family": "wan", "duration_s": 5},
    ])
    assert any(g["batch_eligible"] and set(g["shot_ids"]) == {"A", "B"} for g in plan["batch_groups"])
    assert plan["quality_floor_unchanged"] is True

def test_speculative_budget_is_qc_gated_by_shot_role():
    assert speculative_budget({"purpose": "hero", "generation": {}}) == 2
    assert speculative_budget({"purpose": "background", "generation": {}}) == 1
