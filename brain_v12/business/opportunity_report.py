"""Compact commercial opportunity report."""
from __future__ import annotations
from .opportunity_ranker import rank

def build_report(items: list[dict]) -> dict:
    ranked=rank(items)
    return {
        "total_input":len(items),
        "unique_opportunities":len(ranked),
        "ready_for_review":[x for x in ranked if x["evidence_score"] >= 60],
        "needs_more_evidence":[x for x in ranked if x["evidence_score"] < 60],
    }
