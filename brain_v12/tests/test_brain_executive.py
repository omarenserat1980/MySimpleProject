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


def test_risk_percent_is_calculated_and_bounded():
    low = CompanyObjective("low", "low", 10, evidence=100)
    high = CompanyObjective("high", "high", 10, evidence=0, action_class=ActionClass.IRREVERSIBLE)
    assert 0 <= low.risk_percent <= 100
    assert 0 <= high.risk_percent <= 100
    assert high.risk_percent > low.risk_percent
    assert high.risk_band == "HIGH" or high.risk_band == "CRITICAL"


def test_decision_exposes_calculated_risk():
    e = BrainExecutive(CompanyState(objectives=[
        CompanyObjective("build", "build", 10, evidence=80),
    ]))
    d = e.decide()
    assert d.risk_percent == 11.9
    assert d.risk_band == "LOW"
