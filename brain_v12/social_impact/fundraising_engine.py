"""Fundraising campaign economics and evidence gates."""
from dataclasses import dataclass

@dataclass(frozen=True)
class FundraisingPlan:
    campaign_id:str
    goal:float
    expected_donors:int
    acquisition_cost:float
    platform_fee:float
    confidence:float

def net_target_efficiency(x:FundraisingPlan)->float:
    if x.goal<=0 or x.expected_donors<0 or min(x.acquisition_cost,x.platform_fee,x.confidence)<0:
        raise ValueError("invalid fundraising plan")
    if x.expected_donors==0: return 0.0
    return (x.goal-x.acquisition_cost-x.platform_fee)/x.expected_donors

def campaign_ready(x:FundraisingPlan)->bool:
    return x.goal>0 and x.expected_donors>0 and x.confidence>=.70
