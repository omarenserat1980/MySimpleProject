from brain_v7.braincore_v2.experiment_engine import create,complete
from brain_v7.braincore_v2.health_monitor import check
from brain_v7.braincore_v2.recovery import decide
def test_experiment_requires_evidence(tmp_path,monkeypatch):
    import brain_v7.braincore_v2.experiment_engine as e
    monkeypatch.setattr(e,"PATH",tmp_path/"e.json")
    x=create("copy improves conversion","conversion",0.1)
    y=complete(x["id"],0.12,"test evidence")
    assert y["status"]=="COMPLETED"
def test_health_and_recovery():
    assert check()["healthy"] is True
    assert decide(True,True,True).promote is True
    assert decide(False,True,True).rollback is True
