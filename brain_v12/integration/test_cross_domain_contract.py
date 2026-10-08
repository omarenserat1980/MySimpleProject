from brain_v12.integration.cross_domain_contract import *

def test_low_evidence_research():
    o=CrossDomainOpportunity("x",("marketing","commerce"),.5)
    assert safe_action(o)=="RESEARCH"

def test_cross_domain_analysis():
    o=CrossDomainOpportunity("x",("marketing","finance","commerce"),.9)
    assert safe_action(o)=="ANALYZE"

def test_external_side_effects_require_truth_gate():
    o=CrossDomainOpportunity("x",("finance",),.9,True,False)
    assert safe_action(o)=="HOLD"
    o=CrossDomainOpportunity("x",("finance",),.9,True,True)
    assert safe_action(o)=="AUTHORIZATION_REQUIRED"
