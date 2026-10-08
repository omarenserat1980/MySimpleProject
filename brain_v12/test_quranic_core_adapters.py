from brain_v12.brain.quranic_core import (
    QuranicResearchEngine, EvidenceLevel, CounterEvidenceEngine, HumanBenefitEngine
)

def test_counter_evidence_is_explicit():
    e=QuranicResearchEngine()
    a=e.make_evidence(EvidenceLevel.SCIENTIFIC,"source","claim","doi:x",.8)
    b=e.make_evidence(EvidenceLevel.SCIENTIFIC,"source2","opposing","doi:y",.6,{"relation":"counter"})
    result=CounterEvidenceEngine().evaluate("claim",[a,b])
    assert result["counter_evidence_count"] == 1

def test_benefit_layer_is_not_a_fatwa():
    result=HumanBenefitEngine().propose("finding")
    assert result["status"] == "IDEAS_ONLY"
    assert "avoid presenting Brain output as revelation" in result["principles"]

def test_canonical_text_stays_read_only():
    from brain_v12.brain.quranic_core import CanonicalQuranAdapter
    assert not hasattr(CanonicalQuranAdapter, "put")
    assert not hasattr(CanonicalQuranAdapter, "delete")
