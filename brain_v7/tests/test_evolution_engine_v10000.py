from brain_v7.braincore_v2.evolution_engine import evolution_plan, next_step, verify_progress, snapshot


def test_plan_supports_10000_generations():
    plan = evolution_plan(1, 10000)
    assert len(plan) == 10000
    assert plan[0]["generation"] == 1
    assert plan[-1]["generation"] == 10000


def test_progress_continues_to_next_generation():
    assert next_step(range(1, 100))["generation"] == 100
    assert next_step(range(1, 10000))["generation"] == 10000


def test_evidence_gate_at_high_generation():
    assert verify_progress(10000, True, "")["status"] == "BLOCKED"
    assert verify_progress(10000, True, "verified test evidence")["status"] == "VERIFIED"
    assert verify_progress(10000, True, "verified test evidence")["next_generation"] is None


def test_snapshot_target():
    state = snapshot(range(1, 101))
    assert state["target"] == 10000
    assert state["completed_count"] == 100
    assert state["remaining"] == 9900
    assert state["autonomous_side_effects"] is False
