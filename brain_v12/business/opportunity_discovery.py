"""Commercial opportunity discovery from public market signals."""
from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass
class MarketSignal:
    source: str
    problem: str
    customer_segment: str
    evidence: str
    location: str = ""
    urgency: str = "UNKNOWN"

def qualify(signal: MarketSignal) -> dict:
    completeness = all([
        signal.source.strip(),
        signal.problem.strip(),
        signal.customer_segment.strip(),
        signal.evidence.strip(),
    ])
    return {
        **asdict(signal),
        "status": "READY_FOR_REVIEW" if completeness else "INCOMPLETE",
        "external_contact": "REQUIRES_AUTHORIZATION",
    }

def batch(signals: list[MarketSignal]) -> list[dict]:
    return [qualify(s) for s in signals]
