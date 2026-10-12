from brain_v12.marketing.marketing_domains import domain_ids
from brain_v12.marketing.marketing_expert import MarketingAction, MarketingEvidence, decide
from brain_v12.marketing.experiment_engine import MarketingExperiment, gate_experiment

def test_curriculum_contains_core_domains():
    ids=domain_ids()
    assert "strategy" in ids
    assert "consumer" in ids
    assert "growth" in ids
    assert "analytics" in ids
    assert "ai_marketing" in ids

def test_no_evidence_researches_first():
    d=decide(hypothesis="test", success_metric="conversion")
    assert d.action is MarketingAction.RESEARCH

def test_weak_evidence_experiments():
    d=decide(
        hypothesis="test", success_metric="conversion",
        evidence=(MarketingEvidence("x","conversion",.1,.4,10),),
    )
    assert d.action is MarketingAction.EXPERIMENT

def test_paid_experiment_requires_approval():
    e=MarketingExperiment("e1","test","search","conversion",.1,.2,5)
    assert gate_experiment(e,approved=False,evidence_confidence=.8) == "APPROVAL_REQUIRED"
