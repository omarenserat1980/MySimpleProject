from brain_v7.braincore_v2.evolution_engine import (
    evolution_plan,
    next_step,
    snapshot,
    verify_progress,
)


def test_plan_has_100_generations():
    plan = evolution_plan()
    assert len(plan) == 10000
    assert plan[0]["generation"] == 1
    assert plan[-1]["generation"] == 10000


def test_next_step_advances():
    assert next_step([])["generation"] == 1
    assert next_step(range(1, 10))["generation"] == 10


def test_progress_requires_evidence():
    assert verify_progress(1, True, "")["status"] == "BLOCKED"
    assert verify_progress(1, True, "test evidence")["status"] == "VERIFIED"


def test_snapshot():
    state = snapshot(range(1, 6))
    assert state["completed_count"] == 5
    assert state["remaining"] == 9995
    assert state["autonomous_side_effects"] is False
