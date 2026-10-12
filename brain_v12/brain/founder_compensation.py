"""Founder compensation eligibility planner.

Brain-owned planning only. This module never initiates a payment.
"""
from __future__ import annotations

class FounderCompensationPlanner:
    def __init__(self, founder_share_limit=0.10):
        if not 0 < founder_share_limit <= 1:
            raise ValueError("invalid_founder_share_limit")
        self.founder_share_limit = float(founder_share_limit)

    def evaluate(
        self,
        verified_revenue,
        verified_costs,
        protected_reserves,
        approved_reinvestment,
        proposed_amount,
        currency="JOD",
        destination_ref=None,
        payment_verified=False,
        approval_id=None,
    ):
        values = [verified_revenue, verified_costs, protected_reserves,
                  approved_reinvestment, proposed_amount]
        if any(float(v) < 0 for v in values):
            return {"status": "BLOCKED", "reason": "negative_value"}

        free_cash = float(verified_revenue) - float(verified_costs)
        available = free_cash - float(protected_reserves) - float(approved_reinvestment)
        maximum = max(0.0, available * self.founder_share_limit)

        if not destination_ref:
            return {"status": "BLOCKED", "reason": "payment_destination_not_verified",
                    "maximum_recommended": round(maximum, 8), "currency": currency}

        if float(proposed_amount) > maximum:
            return {"status": "BLOCKED", "reason": "reserve_or_founder_share_limit",
                    "maximum_recommended": round(maximum, 8), "currency": currency}

        if not approval_id:
            return {"status": "APPROVAL_PENDING",
                    "maximum_recommended": round(maximum, 8), "currency": currency}

        if not payment_verified:
            return {"status": "PAYMENT_AUTHORIZATION_READY",
                    "maximum_recommended": round(maximum, 8), "currency": currency,
                    "approval_id": approval_id, "destination_ref": destination_ref}

        return {"status": "PAYMENT_VERIFIED",
                "maximum_recommended": round(maximum, 8), "currency": currency,
                "approval_id": approval_id, "destination_ref": destination_ref}
