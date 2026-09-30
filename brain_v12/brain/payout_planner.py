"""Profit-preserving payout planner.

Plans a payout only from VERIFIED_RECEIVED funds. It never initiates a transfer.
"""
from __future__ import annotations
from .economic_ledger import EconomicLedger
from .authorization_gate import AuthorizationGate

class PayoutPlanner:
    def __init__(self, ledger=None, gate=None):
        self.ledger=ledger or EconomicLedger()
        self.gate=gate or AuthorizationGate()

    def plan_to_owner(self, amount, currency="JOD", destination_label="orange_money",
                      owner_approval=False, approval_id=None):
        verified=self.ledger.verified_total(currency)
        amount=float(amount)
        if amount<=0: return {"status":"DENIED","reason":"amount_must_be_positive"}
        if amount>verified: return {"status":"DENIED","reason":"insufficient_verified_revenue","verified":verified}
        decision=self.gate.decide(
            "move_money",principal="brain",risk="high",
            resource={"destination":destination_label,"amount":amount,"currency":currency},
            requires_owner_approval=True,approved=owner_approval,approval_id=approval_id)
        if decision["decision"]!="ALLOW":
            return {"status":"AWAITING_OWNER_APPROVAL","authorization":decision,"verified":verified}
        return {
            "status":"READY_FOR_PAYMENT_ADAPTER",
            "amount":amount,"currency":currency,"destination":destination_label,
            "verified_revenue":verified,"authorization":decision
        }

if __name__=="__main__":
    print(PayoutPlanner().plan_to_owner(1))
