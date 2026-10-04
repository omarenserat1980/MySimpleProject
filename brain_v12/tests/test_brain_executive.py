from brain_v12.brain.brain_executive import (
    ActionClass, BrainExecutive, CompanyObjective, CompanyState,
)


def test_executive_selects_highest_value_internal_action():
    e = BrainExecutive(CompanyState(objectives=[
        CompanyObjective("low", "low", 1),
        CompanyObjective("high", "high", 10),
    ]))
    d = e.decide()
    assert d.objective_id == "high"
    assert d.status == "READY"


def test_external_side_effect_is_gated():
    e = BrainExecutive(CompanyState(objectives=[
        CompanyObjective("money", "move money", 100, action_class=ActionClass.FINANCIAL),
    ]))
    d = e.decide()
    assert d.status == "GATED"
    assert "authority_gate_required" in d.reason


def test_cycle_is_evidence_of_state_change():
    e = BrainExecutive(CompanyState(objectives=[
        CompanyObjective("build", "build product", 5),
    ]))
    d = e.run_cycle()
    assert d.status == "READY"
    assert "build" in e.state.completed
    assert e.state.cycle == 1


def test_empty_company_enters_discovery():
    e = BrainExecutive()
    d = e.run_cycle()
    assert d.status == "NO_OBJECTIVE"
    assert d.action == "OBSERVE_AND_DISCOVER"
