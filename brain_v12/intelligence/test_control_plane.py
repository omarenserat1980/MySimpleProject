from brain_v12.intelligence.control_plane import *
from brain_v12.intelligence.evidence_registry import *

def test_research_without_evidence():
    r=synthesize((DomainSignal("economic",.8,0,.1),))
    assert r.action is Action.RESEARCH

def test_hold_on_high_risk():
    r=synthesize((DomainSignal("defense",.9,4,.8),))
    assert r.action is Action.HOLD

def test_scenario_with_cross_domain_evidence():
    r=synthesize((DomainSignal("social",.8,2,.1),DomainSignal("economic",.9,3,.2)))
    assert r.action is Action.SCENARIO

def test_evidence_fingerprint():
    e=Evidence("1","economic","claim","source","2026-10-08T00:00:00Z",.9)
    assert validate(e)
    assert len(e.fingerprint())==64
