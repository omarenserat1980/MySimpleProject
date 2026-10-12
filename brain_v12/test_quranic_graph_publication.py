from brain.quranic_core.models import EvidenceLevel,QuranicFinding
from brain.quranic_core.engine import QuranicResearchEngine
from brain.quranic_core.graph import EvidenceGraph
from brain.quranic_core.publication import PublicationGate

def test_graph_marks_counter_evidence():
    e=QuranicResearchEngine()
    a=e.make_evidence(EvidenceLevel.SCIENTIFIC,"paper","counter","doi:x",.8,{"relation":"counter"})
    g=EvidenceGraph().build(QuranicFinding("q","f",[a]))
    assert a.id in g["counter_evidence"]

def test_publication_always_requires_human_review():
    e=QuranicResearchEngine()
    a=e.make_evidence(EvidenceLevel.HUMAN_KNOWLEDGE,"book","claim","p1")
    b=e.make_evidence(EvidenceLevel.SCIENTIFIC,"paper","counter","doi:x",.8,{"relation":"counter"})
    r=PublicationGate().evaluate(QuranicFinding("q","f",[a,b]))
    assert r["status"]=="HUMAN_REVIEW" and r["publish"] is False
