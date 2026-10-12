from brain_v12.finance.finance_engine import *
from brain_v12.business.project_factory import *

def test_finance_needs_evidence():
    x=FinancialOpportunity("a",100,0.2,.1,.9,.4,12)
    assert evaluate(x) is FinanceAction.RESEARCH

def test_project_qualification():
    x=ProjectOpportunity("p","video marketing","SMB","10 videos",500,200,.9)
    assert qualify(x)
    assert gross_margin(x)==.6
