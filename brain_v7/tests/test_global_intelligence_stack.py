from brain_v7.braincore_v2.evidence_engine import Evidence,score
from brain_v7.braincore_v2.market_risk_engine import RiskInputs,score as risk
from brain_v7.braincore_v2.market_matrix import MarketCase,analyze
from brain_v7.braincore_v2.portfolio_engine import allocate

def test_evidence_is_bounded():
    assert 0<=score(Evidence("x","official","official",True))<=1

def test_risk_is_bounded():
    assert 0<=risk(RiskInputs(10,10,10,10,10,10))["overall_risk"]<=10

def test_market_requires_evidence_data():
    r=analyze(MarketCase("JO","pump",100,None,()))
    assert r["status"]=="RESEARCH_REQUIRED"

def test_portfolio_never_authorizes_purchase():
    r=allocate([{"status":"EVIDENCE_REVIEW","gross_profit_jod":20,"evidence_quality":.9}])
    assert r[0]["requires_human_approval"] is True
