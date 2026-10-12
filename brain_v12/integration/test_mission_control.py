from brain_v12.integration.mission_control import plan

def test_low_evidence_research():
    p=plan("evaluate an Amazon business", evidence_confidence=.40)
    assert "commerce" in p.route.specialists
    assert p.action=="RESEARCH"
    assert len(p.mission_fingerprint)==64

def test_external_side_effect_requires_authorization():
    p=plan("publish a product listing", evidence_confidence=.95, external_side_effects=True)
    assert p.action=="AUTHORIZATION_REQUIRED"
    assert p.requires_authorization is True

def test_high_evidence_analysis():
    p=plan("analyze marketing growth", evidence_confidence=.90)
    assert p.action=="ANALYZE"

def test_same_mission_is_deterministic():
    a=plan("same mission", .8)
    b=plan("same mission", .8)
    assert a.mission_fingerprint==b.mission_fingerprint
