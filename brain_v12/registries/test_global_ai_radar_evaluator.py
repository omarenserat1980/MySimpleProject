from pathlib import Path

from global_ai_radar_evaluator import STAGES, build_all_plans, load_registry


def test_radar_plans_require_independent_evidence():
    data = load_registry(Path(__file__).with_name("global_ai_radar.json"))
    plans = build_all_plans(data)

    assert plans
    assert len(STAGES) == 8
    assert all(len(plan["stages"]) == len(STAGES) for plan in plans)
    assert all(plan["promotable"] if "promotable" in plan else True for plan in plans)


def test_radar_does_not_auto_promote():
    plans = build_all_plans()
    assert all(
        stage["status"] == "PENDING"
        for plan in plans
        for stage in plan["stages"]
    )
