from brain_v12.commerce.commerce_engine import *
from brain_v12.commerce.supply_chain import *

def test_profitable_opportunity():
    o=CommerceOpportunity("x",Channel.AMAZON,10,2,2,3,30,10,.9)
    assert decide(o) is CommerceAction.TEST
    assert o.expected_profit==130

def test_low_confidence_research():
    o=CommerceOpportunity("x",Channel.DROPSHIPPING,10,2,2,3,30,10,.4)
    assert decide(o) is CommerceAction.RESEARCH

def test_landed_cost():
    q=SupplierQuote("s",5,10,7,20,.9,True)
    sh=ShippingQuote("x",20,10,True)
    assert landed_unit_cost(q,sh,10)==7
