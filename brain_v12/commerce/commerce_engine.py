"""Unified commerce decision primitives for Brain."""
from dataclasses import dataclass
from enum import Enum

class CommerceAction(str, Enum):
    RESEARCH="RESEARCH"; TEST="TEST"; LIST="LIST"; SCALE="SCALE"; HOLD="HOLD"; STOP="STOP"

class Channel(str, Enum):
    INTERNAL="INTERNAL"; AMAZON="AMAZON"; EBAY="EBAY"; TEMU="TEMU"; ALIBABA="ALIBABA"; DROPSHIPPING="DROPSHIPPING"; OTHER="OTHER"

@dataclass(frozen=True)
class CommerceOpportunity:
    opportunity_id:str
    channel:Channel
    product_cost:float
    shipping_cost:float
    platform_fees:float
    marketing_cost:float
    expected_price:float
    expected_units:float
    confidence:float
    policy_risk:float=.0

    @property
    def unit_cost(self): return self.product_cost+self.shipping_cost+self.platform_fees+self.marketing_cost
    @property
    def expected_profit(self): return (self.expected_price-self.unit_cost)*self.expected_units
    @property
    def margin(self):
        return (self.expected_price-self.unit_cost)/self.expected_price if self.expected_price>0 else -1

def decide(op:CommerceOpportunity)->CommerceAction:
    if min(op.product_cost,op.shipping_cost,op.platform_fees,op.marketing_cost,op.expected_price,op.expected_units)<0: raise ValueError("negative commerce input")
    if op.policy_risk>.5: return CommerceAction.STOP
    if op.confidence<.70: return CommerceAction.RESEARCH
    if op.expected_profit<=0 or op.margin<.15: return CommerceAction.HOLD
    return CommerceAction.TEST if op.expected_units<100 else CommerceAction.SCALE
