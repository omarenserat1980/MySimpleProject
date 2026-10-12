"""Evidence-driven Marketing Expert decision engine."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class MarketingAction(str, Enum):
    LEARN="LEARN"
    RESEARCH="RESEARCH"
    EXPERIMENT="EXPERIMENT"
    OPTIMIZE="OPTIMIZE"
    SCALE="SCALE"
    HOLD="HOLD"

@dataclass(frozen=True)
class MarketingEvidence:
    source: str
    metric: str
    value: float
    confidence: float
    sample_size: int = 0

@dataclass(frozen=True)
class MarketingDecision:
    action: MarketingAction
    hypothesis: str
    success_metric: str
    rationale: str
    confidence: float

def decide(
    *,
    hypothesis: str,
    success_metric: str,
    evidence: tuple[MarketingEvidence, ...] = (),
    budget_usd: float = 0,
) -> MarketingDecision:
    if budget_usd < 0:
        raise ValueError("budget_usd must be non-negative")
    if not hypothesis.strip() or not success_metric.strip():
        raise ValueError("hypothesis and success_metric are required")
    if not evidence:
        return MarketingDecision(
            MarketingAction.RESEARCH, hypothesis, success_metric,
            "No evidence: research before spending or scaling.", 0.0,
        )
    confidence=sum(max(0,min(1,e.confidence)) for e in evidence)/len(evidence)
    sample=sum(max(0,e.sample_size) for e in evidence)
    if confidence < .70 or sample < 30:
        return MarketingDecision(
            MarketingAction.EXPERIMENT, hypothesis, success_metric,
            "Evidence is insufficient for scaling; run a bounded experiment.", confidence,
        )
    return MarketingDecision(
        MarketingAction.OPTIMIZE, hypothesis, success_metric,
        "Evidence is sufficient for optimization; scaling still requires a separate gate.", confidence,
    )
