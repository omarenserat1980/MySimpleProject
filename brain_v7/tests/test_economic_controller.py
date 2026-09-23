from brain_v7.braincore_v2.economic_controller import evaluate
from brain_v7.braincore_v2.revenue_engine import Opportunity

def test_economic_controller_never_claims_payment():
    x=evaluate(Opportunity("demo","product_copy",10,0.5,0.8,0.9,0.1))
    assert x.expected_jod==10
    assert x.requires_approval is True
    assert "unverified" in x.rationale
