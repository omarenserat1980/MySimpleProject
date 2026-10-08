"""Grant and fundraising planning without claiming awards or donations."""
from dataclasses import dataclass

@dataclass(frozen=True)
class GrantOpportunity:
    grant_id:str
    funder:str
    eligible_region:str
    cause_fit:float
    deadline_days:int
    award_amount:float
    match_required:float
    confidence:float

def score_grant(x:GrantOpportunity)->float:
    if min(x.cause_fit,x.award_amount,x.match_required,x.confidence)<0 or x.deadline_days<0:
        raise ValueError("invalid grant data")
    urgency=1/(1+x.deadline_days)
    return .35*x.cause_fit+.30*x.confidence+.20*urgency+.15*(1-min(x.match_required,1))

def grant_ready(x:GrantOpportunity)->bool:
    return x.cause_fit>=.70 and x.confidence>=.70 and x.award_amount>0
