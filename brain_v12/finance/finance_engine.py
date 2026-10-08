"""Finance and investment decision guardrails. Analysis only; no money movement."""
from dataclasses import dataclass
from enum import Enum

class FinanceAction(str,Enum):
    RESEARCH="RESEARCH"; HOLD="HOLD"; CONSIDER="CONSIDER"; REJECT="REJECT"

@dataclass(frozen=True)
class FinancialOpportunity:
    asset_id:str
    capital_required:float
    expected_return:float
    downside:float
    liquidity:float
    evidence_confidence:float
    horizon_months:int

def evaluate(x:FinancialOpportunity)->FinanceAction:
    if min(x.capital_required,x.downside,x.liquidity,x.evidence_confidence,x.horizon_months)<0:
        raise ValueError("invalid financial input")
    if x.capital_required==0 or x.expected_return<=0: return FinanceAction.REJECT
    if x.evidence_confidence<.70: return FinanceAction.RESEARCH
    if x.downside>.35 or x.liquidity<.30: return FinanceAction.HOLD
    return FinanceAction.CONSIDER

def expected_value(x:FinancialOpportunity)->float:
    return x.capital_required*x.expected_return
