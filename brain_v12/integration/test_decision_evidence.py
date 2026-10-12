from brain_v12.integration.decision_evidence import DecisionEvidence

def test_evidence_is_valid_and_fingerprinted():
    e=DecisionEvidence("a"*64,"ANALYZE",("finance",),.9,False,False,"high confidence")
    assert e.valid()
    assert len(e.fingerprint())==64

def test_external_side_effect_requires_authorization():
    e=DecisionEvidence("a"*64,"AUTHORIZATION_REQUIRED",("commerce",),.9,True,True,"external action")
    assert e.valid()

def test_invalid_external_action_cannot_be_valid():
    e=DecisionEvidence("a"*64,"ANALYZE",("commerce",),.9,True,False,"unsafe")
    assert not e.valid()
