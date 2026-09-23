from brain_v7.braincore_v2.global_opportunity_scanner import OpportunityEvidence,evaluate

def test_missing_market_evidence_blocks_buy_decision():
    r=evaluate(OpportunityEvidence("JO","pump",100,None,8,6))
    assert r["status"]=="NEEDS_RESEARCH"
    assert r["decision"]=="NO_BUY_DECISION"

def test_verified_evidence_allows_review_not_autonomous_purchase():
    r=evaluate(OpportunityEvidence("JO","pump",150,90,8,5,3,True))
    assert r["status"]=="EVIDENCE_READY"
    assert r["decision"]=="REVIEW_REQUIRED"
    assert r["gross_profit_jod"]==60
