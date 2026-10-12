from brain_v12.brain.brain_executive import ActionClass, CompanyObjective
from brain_v12.brain.company_executive import CompanyExecutive, ExecutiveSubsystems


def test_company_executive_delegates_verified_internal_work():
    called = []
    c = CompanyExecutive(subsystems=ExecutiveSubsystems(supervisor=object(), memory=object()))
    c.discover_objectives([CompanyObjective("repair", "repair", 10)])
    result = c.cycle(lambda decision: called.append(decision.objective_id) or True)
    assert result["result"] == "COMPLETED"
    assert called == ["repair"]
    assert "supervisor" in result["subsystems"]


def test_company_executive_does_not_execute_gated_financial_work():
    called = []
    c = CompanyExecutive()
    c.discover_objectives([CompanyObjective("payout", "payout", 100, action_class=ActionClass.FINANCIAL)])
    result = c.cycle(lambda _: called.append("executed") or True)
    assert result["result"] == "GATED"
    assert called == []
