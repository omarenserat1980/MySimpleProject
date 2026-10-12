from brain.quranic_core.models import EvidenceLevel
from brain.quranic_core.engine import QuranicResearchEngine
from brain.quranic_core.provenance import ProvenanceEngine

def test_provenance_is_deterministic():
    e=QuranicResearchEngine()
    a=e.make_evidence(EvidenceLevel.HUMAN_KNOWLEDGE,"book","claim",citation="p1")
    b=e.make_evidence(EvidenceLevel.SCIENTIFIC,"paper","result",citation="doi:x")
    x=ProvenanceEngine().build([a,b])
    y=ProvenanceEngine().build([b,a])
    assert x.manifest_id==y.manifest_id and x.evidence_hash==y.evidence_hash

def test_quran_missing_citation_is_incomplete():
    e=QuranicResearchEngine()
    a=e.make_evidence(EvidenceLevel.QURAN_TEXT,"canonical","verse")
    m=ProvenanceEngine().build([a])
    assert m.complete is False
    assert a.id in m.missing_citations
