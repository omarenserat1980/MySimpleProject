"""Normalize and score commercial signals without claiming they are customers."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class LeadSignal:
    source: str
    customer_hint: str
    problem: str
    evidence_url: str = ""
    location: str = ""
    status: str = "UNVERIFIED"

def normalize(signal: LeadSignal) -> dict:
    return {
        "source":signal.source,
        "customer_hint":signal.customer_hint.strip(),
        "problem":signal.problem.strip(),
        "evidence_url":signal.evidence_url,
        "location":signal.location,
        "status":"READY_FOR_REVIEW" if signal.problem.strip() and signal.source.strip() else "INCOMPLETE",
    }
