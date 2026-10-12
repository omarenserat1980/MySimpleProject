"""Supplier and shipping comparison without committing purchases."""
from dataclasses import dataclass

@dataclass(frozen=True)
class SupplierQuote:
    supplier_id:str
    unit_price:float
    moq:int
    lead_days:int
    shipping_total:float
    quality_score:float
    verified:bool=False

@dataclass(frozen=True)
class ShippingQuote:
    provider:str
    cost:float
    transit_days:int
    tracking:bool
    customs_included:bool=False

def landed_unit_cost(quote:SupplierQuote, shipping:ShippingQuote, quantity:int)->float:
    if quantity<=0: raise ValueError("quantity must be positive")
    return quote.unit_price + shipping.cost/quantity

def supplier_score(quote:SupplierQuote, shipping:ShippingQuote)->float:
    if quote.moq<=0 or quote.lead_days<0 or shipping.cost<0: raise ValueError("invalid quote")
    return .35*quote.quality_score + .25*(1/(1+quote.lead_days)) + .20*(1/(1+quote.moq)) + .20*(1/(1+shipping.transit_days))
