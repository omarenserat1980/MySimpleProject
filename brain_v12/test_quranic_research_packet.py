from brain.quranic_core.models import EvidenceLevel,QuranicFinding
from brain.quranic_core.engine import QuranicResearchEngine
from brain.quranic_core.research_packet import ResearchPacketBuilder

def test_packet_is_non_publishable_and_traceable():
    e=QuranicResearchEngine()
    a=e.make_evidence(EvidenceLevel.SCIENTIFIC,"paper","claim","doi:x")
    p=ResearchPacketBuilder().build(QuranicFinding("q","f",[a],["lim"],["alt"]))
    assert p["publishable"] is False
    assert p["packet_id"]
    assert p["decision"]["publish"] is False
    assert p["limitations"]==["lim"]
