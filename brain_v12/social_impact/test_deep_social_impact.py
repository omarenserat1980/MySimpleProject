from brain_v12.social_impact.program_engine import *
from brain_v12.social_impact.due_diligence import *
from brain_v12.social_impact.fundraising_engine import *
from brain_v12.social_impact.social_impact_control import *

def test_program_readiness():
    p=Program("p","education gap","youth",("training",),("graduates",),("employment",),"improved livelihoods",.9)
    assert readiness(p)>.8

def test_due_diligence():
    d=DueDiligence(True,True,True,True,True,True)
    assert suitable_for_partnership(d)

def test_fundraising_gate():
    f=FundraisingPlan("c",10000,100,500,300,.9)
    assert campaign_ready(f)
    assert net_target_efficiency(f)>0

def test_safeguarding_holds():
    c=ImpactControl(.9,.5,.9,.9,.9)
    assert decide(c) is ImpactAction.HOLD
