from brain_v12.brain.quranic_core import EvidenceLevel, QuranicResearchEngine

def test_quran_text_requires_citation():
    e = QuranicResearchEngine().make_evidence(EvidenceLevel.QURAN_TEXT, "Tanzil", "نص", confidence=1)
    r = QuranicResearchEngine().gate.validate([e])
    assert not r.allowed

def test_brain_inference_cannot_be_presented_as_quran():
    e = QuranicResearchEngine().make_evidence(EvidenceLevel.BRAIN_INFERENCE, "Brain", "استنتاج", .7, metadata={"present_as":"quran"})
    assert not QuranicResearchEngine().gate.publication_allowed([e])

def test_pipeline_contains_counter_evidence():
    c = QuranicResearchEngine().pipeline("العلم")
    assert "COUNTER_EVIDENCE" in c["stages"]

def test_clean_research_is_accepted():
    engine = QuranicResearchEngine()
    q = engine.make_evidence(EvidenceLevel.QURAN_TEXT, "Tanzil", "نص موثق", "2:164", 1)
    b = engine.make_evidence(EvidenceLevel.BRAIN_INFERENCE, "Brain", "استنتاج بحثي", confidence=.7)
    f = engine.research("سؤال", [q,b], "نتيجة")
    assert f.status == "VERIFIED_STRUCTURE"
