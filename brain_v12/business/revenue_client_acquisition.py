"""Evidence-first acquisition contract for Brain's first real-revenue customer.

This module deliberately cannot manufacture a customer, payment, revenue, or profit.
It defines the state machine and evidence required to move CL-000003 from prospect
to verified commercial outcome.
"""
from __future__ import annotations

from typing import Any

REVENUE_CLIENT_ID = "CL-000003"

STATES = (
    "PROSPECT",
    "OFFER_PREPARED",
    "CUSTOMER_VALIDATED",
    "PAYMENT_VERIFIED",
    "REVENUE_REALIZED",
    "PROFIT_VERIFIED",
    "CLOSED",
)

REQUIRED_EVIDENCE = {
    "CUSTOMER_VALIDATED": ("customer_acceptance", "order_id"),
    "PAYMENT_VERIFIED": ("payment_receipt", "payment_reference"),
    "REVENUE_REALIZED": (
        "customer_acceptance",
        "order_id",
        "payment_receipt",
        "payment_reference",
        "delivery_evidence",
    ),
    "PROFIT_VERIFIED": (
        "revenue_evidence",
        "attributable_cost_evidence",
    ),
}

# One active request per customer remains a hard rule.
REVENUE_CLIENT = {
    "client_id": REVENUE_CLIENT_ID,
    "kind": "EXTERNAL_REVENUE_CANDIDATE",
    "status": "PROSPECT",
    "active_request_limit": 1,
    "payment_required_for_revenue": True,
    "automatic_contract": False,
    "automatic_payment": False,
    "automatic_withdrawal": False,
}


def validate_transition(state: str, evidence: dict[str, Any]) -> dict[str, Any]:
    """Return whether a commercial state transition has sufficient evidence."""
    if state not in REQUIRED_EVIDENCE:
        return {"ok": True, "state": state, "missing": []}

    missing = [
        key for key in REQUIRED_EVIDENCE[state]
        if not evidence.get(key)
    ]
    return {
        "ok": not missing,
        "state": state,
        "missing": missing,
        "evidence_complete": not missing,
    }


def revenue_realized(evidence: dict[str, Any]) -> bool:
    """Only verified payment + delivery evidence can establish realized revenue."""
    result = validate_transition("REVENUE_REALIZED", evidence)
    return bool(result["ok"])


def profit_verified(evidence: dict[str, Any]) -> bool:
    """Profit requires revenue evidence and attributable cost evidence."""
    result = validate_transition("PROFIT_VERIFIED", evidence)
    return bool(result["ok"])
