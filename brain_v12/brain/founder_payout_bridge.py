"""Founder payout bridge.

Connects founder compensation eligibility to the existing payout planner while
keeping destination identity private and external money movement gated.
"""
from __future__ import annotations

from .founder_compensation import FounderCompensationPlanner
from .payout_planner import PayoutPlanner


class FounderPayoutBridge:
    def __init__(self, compensation=None, payout=None):
        self.compensation = compensation or FounderCompensationPlanner()
        self.payout = payout or PayoutPlanner()

    def prepare(self, amount, currency="JOD", destination_ref=None,
                owner_approval=False, approval_id=None,
                verified_revenue=None, verified_costs=0,
                protected_reserves=0, approved_reinvestment=0):
        if verified_revenue is None:
            verified_revenue = self.payout.ledger.verified_total(currency)

        eligibility = self.compensation.evaluate(
            verified_revenue=verified_revenue,
            verified_costs=verified_costs,
            protected_reserves=protected_reserves,
            approved_reinvestment=approved_reinvestment,
            proposed_amount=amount,
            currency=currency,
            destination_ref=destination_ref,
            payment_verified=False,
            approval_id=approval_id,
        )

        if eligibility["status"] == "BLOCKED":
            return {"status": "BLOCKED", "eligibility": eligibility}

        payout = self.payout.plan_to_owner(
            amount=amount,
            currency=currency,
            destination_label="FOUNDER_PAYMENT_DESTINATION_REF",
            owner_approval=owner_approval,
            approval_id=approval_id,
        )

        return {
            "status": payout["status"],
            "eligibility": eligibility,
            "payout": payout,
            "destination_ref": destination_ref,
        }
