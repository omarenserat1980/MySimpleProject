"""Discover -> select -> execute handoff -> verify -> ledger.

Execution is represented as a gated handoff. External submission is not automated
by this module; it consumes existing Brain capabilities and records evidence.
"""
from __future__ import annotations
from .economic_connectors import OpportunityRouter
from .economic_ledger import EconomicLedger
from .payment_adapters import BaseUSDCAdapter, BinanceAdapter

class EconomicCycle:
    def __init__(self, ledger=None, router=None):
        self.ledger=ledger or EconomicLedger()
        self.router=router or OpportunityRouter()
    def discover(self):
        return self.router.discover()
    def record_claim(self, op, amount, currency, evidence):
        return self.ledger.record(op["opportunity_id"],"CLAIMED",amount,currency,evidence,{"source":op["source"]})
    def verify_and_record(self, op_id, receipt, adapter):
        result=adapter.verify_receipt(receipt)
        if not result.get("verified"):
            return {"status":"REJECTED","verification":result}
        return self.ledger.record(op_id,"VERIFIED_RECEIVED",float(receipt["amount"]),receipt["currency"],
                                  {**result["evidence"],"receipt_hash":receipt.get("receipt_hash")},{"adapter":adapter.name})
    def payout_plan(self, amount, currency, destination, authorization):
        if currency=="USDC": return BaseUSDCAdapter().payout({"amount":amount,"currency":currency,"destination":destination},authorization)
        return BinanceAdapter().payout({"amount":amount,"currency":currency,"destination":destination},authorization)
