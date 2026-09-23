"""Allowlisted payout destinations with explicit verification state."""
from __future__ import annotations
def add(registry:dict,ref:str,verified:bool=False)->dict:
    if not ref.strip(): raise ValueError("empty destination")
    registry[ref]={"verified":bool(verified)}
    return registry
def can_pay(registry:dict,ref:str)->bool:
    return bool(registry.get(ref,{}).get("verified"))
