from brain.quranic_core.models import QuranicFinding
from brain.quranic_core.knowledge import KnowledgeOpportunityEngine

def test_opportunities_are_reviewable():
    r=KnowledgeOpportunityEngine().generate(QuranicFinding("q","نتيجة",[ ]))
    assert r["status"]=="IDEAS_ONLY"
    assert all(x["requires_review"] for x in r["opportunities"])
