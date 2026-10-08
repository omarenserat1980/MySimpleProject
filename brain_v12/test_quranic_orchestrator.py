from brain_v12.brain.quranic_core.orchestrator import QuranicResearchOrchestrator
from brain_v12.brain.quranic_core.models import EvidenceLevel

def ev(level,source,claim,citation="ref",confidence=.8,metadata=None):
    return {"level":level,"source":source,"claim":claim,"citation":citation,"confidence":confidence,"metadata":metadata or {}}

def test_orchestrator_holds_without_counter_evidence():
    o=QuranicResearchOrchestrator()
    r=o.evaluate("سؤال","نتيجة",[ev(EvidenceLevel.SCIENTIFIC,"S","دليل")])
    assert r["status"]=="HOLD"
    assert r["stage"]=="COUNTER_EVIDENCE"

def test_orchestrator_reaches_human_review_after_counter():
    o=QuranicResearchOrchestrator()
    r=o.evaluate("سؤال","نتيجة",[
        ev(EvidenceLevel.SCIENTIFIC,"S","دليل"),
        ev(EvidenceLevel.SCIENTIFIC,"C","دليل مضاد",metadata={"relation":"counter"})
    ])
    assert r["status"]=="READY_FOR_HUMAN_REVIEW"
    assert r["next"]=="human_review_before_publication"
