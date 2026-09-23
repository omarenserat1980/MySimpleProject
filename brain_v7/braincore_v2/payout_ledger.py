"""Append-only local payout ledger with idempotency and reconciliation."""
from __future__ import annotations
from dataclasses import dataclass,asdict
from datetime import datetime,timezone
import hashlib,json

@dataclass(frozen=True)
class LedgerEntry:
    request_id:str
    amount_jod:float
    destination_ref:str
    status:str
    provider_reference:str|None=None
    created_at:str=""

def request_id(amount:float,destination:str,nonce:str)->str:
    raw=f"{amount:.2f}|{destination}|{nonce}".encode()
    return hashlib.sha256(raw).hexdigest()

def append(entries:list[LedgerEntry],entry:LedgerEntry)->list[LedgerEntry]:
    if any(e.request_id==entry.request_id for e in entries):
        return entries
    return [*entries,entry]

def reconcile(entry:LedgerEntry,provider_status:str,provider_reference:str|None)->LedgerEntry:
    if provider_status=="CONFIRMED" and not provider_reference:
        raise ValueError("confirmed transfer requires provider reference")
    return LedgerEntry(entry.request_id,entry.amount_jod,entry.destination_ref,
                       provider_status,provider_reference,entry.created_at or datetime.now(timezone.utc).isoformat())
