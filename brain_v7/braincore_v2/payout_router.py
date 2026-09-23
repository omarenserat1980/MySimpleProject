"""Provider-agnostic payout orchestration. No credentials are handled here."""
from __future__ import annotations
from dataclasses import dataclass
from .payout_policy import PayoutPolicy,authorize
from .payout_ledger import LedgerEntry,request_id,append,reconcile

@dataclass
class PayoutRouter:
    policy:PayoutPolicy
    ledger:list[LedgerEntry]

    def prepare(self,amount_jod:float,destination_ref:str,nonce:str,spent_today_jod:float,reason:str)->dict:
        decision=authorize(amount_jod,destination_ref,spent_today_jod,self.policy)
        rid=request_id(amount_jod,destination_ref,nonce)
        if not decision["allowed"]:
            return {"status":"BLOCKED","request_id":rid,**decision}
        entry=LedgerEntry(rid,round(amount_jod,2),destination_ref,"APPROVAL_REQUIRED")
        self.ledger=append(self.ledger,entry)
        return {"status":"APPROVAL_REQUIRED","request_id":rid,"reason":reason,**decision}

    def reconcile_provider(self,request_id_value:str,status:str,provider_reference:str|None=None)->dict:
        for i,e in enumerate(self.ledger):
            if e.request_id==request_id_value:
                self.ledger[i]=reconcile(e,status,provider_reference)
                return {"status":self.ledger[i].status,"request_id":request_id_value,
                        "provider_reference":self.ledger[i].provider_reference}
        return {"status":"NOT_FOUND","request_id":request_id_value}
