from brain_v7.braincore_v2.governance import evaluate_action,policy_snapshot
from brain_v7.braincore_v2.learning_loop import record,confidence
def test_money_transfer_is_blocked():
    d=evaluate_action("transfer_money"); assert not d.allowed and d.requires_approval
def test_irreversible_action_requires_approval():
    d=evaluate_action("web_publish",irreversible=True); assert d.allowed and d.requires_approval
def test_learning_requires_evidence(tmp_path,monkeypatch):
    import brain_v7.braincore_v2.learning_loop as ll
    monkeypatch.setattr(ll,"PATH",tmp_path/"memory.json")
    record("math","npv",passed=True,evidence="unit test passed")
    assert confidence("math","npv")>0
    assert policy_snapshot()["autonomous_money_movement"] is False
