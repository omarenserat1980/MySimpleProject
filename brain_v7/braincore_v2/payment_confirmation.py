"""Provider-confirmation and reconciliation stage for real transfers."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class Confirmation:
    status: str
    provider_reference: str
    amount_jod: float | None
    reason: str

class StatusProvider(Protocol):
    def status(self, provider_reference: str): ...

def reconcile_confirmation(*, requested_amount_jod: float,
                           provider_reference: str,
                           provider_result) -> Confirmation:
    if not provider_reference.strip():
        return Confirmation("FAILED","",None,"Missing provider reference.")
    status=str(getattr(provider_result,"status",None) or
               (provider_result.get("status","") if isinstance(provider_result,dict) else "")).upper()
    amount=getattr(provider_result,"amount_jod",None)
    if amount is None and isinstance(provider_result,dict):
        amount=provider_result.get("amount_jod")
    if amount is not None and round(float(amount),2) != round(requested_amount_jod,2):
        return Confirmation("FAILED",provider_reference,amount,"Provider amount mismatch.")
    if status in {"CONFIRMED","COMPLETED"}:
        return Confirmation("CONFIRMED",provider_reference,amount,"Provider confirmed the transfer.")
    if status in {"FAILED","REVERSED"}:
        return Confirmation(status,provider_reference,amount,"Provider reported a terminal failure.")
    return Confirmation("PENDING",provider_reference,amount,"Provider has not confirmed completion.")
