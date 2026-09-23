"""Safe payout request layer for the Electronic Brain.

It prepares a payout request for a user-owned payment account. It never stores
payment credentials and never claims that a transfer happened without an
external provider confirmation.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class PayoutStatus(str,Enum):
    REQUESTED="REQUESTED"
    APPROVAL_REQUIRED="APPROVAL_REQUIRED"
    SUBMITTED="SUBMITTED"
    CONFIRMED="CONFIRMED"
    FAILED="FAILED"

@dataclass(frozen=True)
class PayoutRequest:
    amount_jod: float
    destination_ref: str
    reason: str
    requires_approval: bool = True

def create_payout(amount_jod:float,destination_ref:str,reason:str)->dict:
    if amount_jod <= 0:
        raise ValueError("amount must be positive")
    if not destination_ref.strip():
        raise ValueError("destination reference is required")
    # Credentials/PINs/tokens must remain outside this module.
    return {
        "status":PayoutStatus.APPROVAL_REQUIRED.value,
        "amount_jod":round(amount_jod,2),
        "destination_ref":destination_ref,
        "reason":reason,
        "credentials_requested":False,
        "provider_confirmation_required":True,
    }

def confirm_payout(provider_reference:str)->dict:
    if not provider_reference.strip():
        raise ValueError("provider reference required")
    return {"status":PayoutStatus.CONFIRMED.value,
            "provider_reference":provider_reference}
