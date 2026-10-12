from brain_v12.marketing.knowledge_graph import (
    KnowledgeNode, KnowledgeEdge, MarketingKnowledgeGraph
)
from brain_v12.marketing.marketing_memory import MarketingObservation, accept_observation

def test_graph_requires_known_nodes():
    g=MarketingKnowledgeGraph()
    g.add_node(KnowledgeNode("n1","framework","STP","strategy"))
    g.add_node(KnowledgeNode("n2","experiment","segmentation test","strategy"))
    g.link(KnowledgeEdge("n1","tested_by","n2",("evidence-1",)))
    assert g.evidence_backed("n1")

def test_observation_validation():
    o=MarketingObservation("o1","seo","SEO improves qualified traffic","qualified_traffic",.2,"analytics",.9)
    assert accept_observation(o)
