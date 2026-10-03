"""Read-only audit bridge for mining opportunity intelligence.

This module converts an opportunity report into an auditable analysis record.
It deliberately cannot verify payment, realize revenue, move funds, purchase
hashpower, create contracts, or trigger withdrawals.
"""
from __future__ import annotations

from typing import Any


def build_mining_opportunity_audit_record(
    report: dict[str, Any],
    *,
    opportunity_id: str,
) -> dict[str, Any]:
    """Create a non-financial ledger-style record from an opportunity report."""
    if not opportunity_id.strip():
        raise ValueError("opportunity_id is required")
    if report.get("engine") != "Brain Mining Opportunity Intelligence":
        raise ValueError("unsupported opportunity report")
    policy = report.get("decision_policy", {})
    if policy.get("read_only") is not True:
        raise ValueError("opportunity report must be read-only")
    return {
        "record_type": "MINING_OPPORTUNITY_ANALYSIS",
        "opportunity_id": opportunity_id,
        "analysis_only": True,
        "status": "ANALYSIS_ONLY",
        "market_evidence": report.get("market_evidence", {}),
        "workers": report.get("workers", []),
        "decision_policy": {
            "read_only": True,
            "auto_purchase": False,
            "auto_contract": False,
            "auto_withdrawal": False,
            "funds_moved_by_brain": False,
            "revenue_realized": False,
            "human_approval_required_for_external_action": True,
        },
    }
