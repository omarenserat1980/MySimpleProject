"""Bounded marketing experimentation primitives."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class ExperimentStatus(str, Enum):
    PROPOSED="PROPOSED"
    APPROVED="APPROVED"
    RUNNING="RUNNING"
    MEASURED="MEASURED"
    ACCEPTED="ACCEPTED"
    REJECTED="REJECTED"

@dataclass(frozen=True)
class MarketingExperiment:
    experiment_id: str
    hypothesis: str
    channel: str
    primary_metric: str
    baseline: float
    target: float
    budget_usd: float
    status: ExperimentStatus = ExperimentStatus.PROPOSED

    def validate(self) -> None:
        if not self.experiment_id or not self.hypothesis or not self.channel or not self.primary_metric:
            raise ValueError("experiment identity and measurement fields are required")
        if self.budget_usd < 0:
            raise ValueError("budget_usd must be non-negative")

def gate_experiment(experiment: MarketingExperiment, *, approved: bool, evidence_confidence: float) -> str:
    experiment.validate()
    if experiment.budget_usd > 0 and not approved:
        return "APPROVAL_REQUIRED"
    if evidence_confidence < 0 or evidence_confidence > 1:
        raise ValueError("evidence_confidence must be between 0 and 1")
    if evidence_confidence < .50:
        return "RESEARCH_REQUIRED"
    return "EXPERIMENT_ALLOWED"
