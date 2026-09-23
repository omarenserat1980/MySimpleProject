"""Reasoning quality controller.

Turns measurable reasoning signals into conservative improvement recommendations.
It never claims external success without evidence.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from time import time


@dataclass
class QualityReport:
    understanding_confidence: float
    evidence_coverage: float
    contradiction_rate: float
    alternative_count: int
    reversibility: float
    overall: float
    recommendations: list[str]
    timestamp: float


class ReasoningQualityController:
    def __init__(self, max_history: int = 200) -> None:
        self.max_history = max_history
        self.history: list[QualityReport] = []

    @staticmethod
    def _clamp(v: float) -> float:
        return max(0.0, min(1.0, float(v)))

    def evaluate(
        self,
        *,
        understanding_confidence: float,
        evidence_count: int,
        contradiction_count: int,
        alternative_count: int,
        reversibility: float,
    ) -> QualityReport:
        evidence_coverage = self._clamp(evidence_count / max(1, alternative_count))
        contradiction_rate = self._clamp(
            contradiction_count / max(1, evidence_count + contradiction_count)
        )
        alt_factor = self._clamp(alternative_count / 3.0)
        overall = self._clamp(
            0.35 * understanding_confidence
            + 0.20 * evidence_coverage
            + 0.15 * (1.0 - contradiction_rate)
            + 0.15 * alt_factor
            + 0.15 * reversibility
        )
        recommendations: list[str] = []
        if understanding_confidence < 0.60:
            recommendations.append("increase_context_collection")
        if evidence_coverage < 0.60:
            recommendations.append("seek_more_evidence")
        if contradiction_rate > 0.35:
            recommendations.append("retest_conflicting_hypotheses")
        if alternative_count < 3:
            recommendations.append("generate_more_alternatives")
        if reversibility < 0.50:
            recommendations.append("prefer_reversible_plan")
        if not recommendations:
            recommendations.append("continue_with_current_reasoning")
        report = QualityReport(
            understanding_confidence=self._clamp(understanding_confidence),
            evidence_coverage=evidence_coverage,
            contradiction_rate=contradiction_rate,
            alternative_count=alternative_count,
            reversibility=self._clamp(reversibility),
            overall=overall,
            recommendations=recommendations,
            timestamp=time(),
        )
        self.history.append(report)
        self.history = self.history[-self.max_history:]
        return report

    def snapshot(self) -> dict:
        return {
            "history_size": len(self.history),
            "latest": asdict(self.history[-1]) if self.history else None,
        }
