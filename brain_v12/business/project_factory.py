"""Project-to-revenue factory: identifies and structures work, never fabricates income."""
from dataclasses import dataclass
from enum import Enum

class ProjectStage(str,Enum):
    IDEA="IDEA"; VALIDATED="VALIDATED"; OFFER_READY="OFFER_READY"; AUTHORIZED="AUTHORIZED"; DELIVERED="DELIVERED"; PAID="PAID"

@dataclass(frozen=True)
class ProjectOpportunity:
    project_id:str
    problem:str
    buyer:str
    deliverable:str
    expected_price:float
    delivery_cost:float
    confidence:float
    stage:ProjectStage=ProjectStage.IDEA

def gross_margin(x:ProjectOpportunity)->float:
    if x.expected_price<=0: return -1
    return (x.expected_price-x.delivery_cost)/x.expected_price

def qualify(x:ProjectOpportunity)->bool:
    return bool(x.problem and x.buyer and x.deliverable and x.expected_price>0 and x.delivery_cost>=0 and x.confidence>=.70 and gross_margin(x)>=.30)
