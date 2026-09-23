"""Internal intelligence and security center.

Collects authorized data from configured sources, normalizes evidence, scores
opportunities and risks, and feeds the Brain's defensive decision pipeline.
It does not hack, evade access controls, or target private individuals.
Political information is handled as neutral, sourced information.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

@dataclass
class IntelligenceReport:
    report_id: str
    domain: str
    source: str
    summary: str
    evidence: dict[str, Any]
    confidence: float
    impact: float
    actionability: float
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class IntelligenceCenter:
    DOMAINS = (
        "MARKETS", "BUSINESS", "TECHNOLOGY", "SCIENCE", "MEDIA",
        "SECURITY", "OPERATIONS", "FINANCE", "REGULATION", "POLITICS",
        "HEALTH", "LEARNING", "OPPORTUNITIES",
    )

    def __init__(self, notifications=None) -> None:
        self.notifications = notifications
        self.reports: list[IntelligenceReport] = []
        self.watchlists: dict[str, list[str]] = {}
        self._counter = 0

    def _id(self) -> str:
        self._counter += 1
        return f"INTEL-{self._counter:07d}"

    def ingest(self, domain: str, source: str, summary: str,
               evidence: dict[str, Any] | None = None,
               confidence: float = 0.5, impact: float = 0.5,
               actionability: float = 0.5) -> IntelligenceReport:
        domain = domain.upper()
        if domain not in self.DOMAINS:
            domain = "OPERATIONS"
        clamp = lambda x: max(0.0, min(1.0, float(x)))
        report = IntelligenceReport(
            self._id(), domain, source, summary, evidence or {},
            clamp(confidence), clamp(impact), clamp(actionability)
        )
        self.reports.append(report)
        if self.notifications:
            self.notifications.emit(
                "INTELLIGENCE_REPORT",
                sender_id="INTEL-CORE",
                recipient_id="BRAIN-001",
                message=f"New intelligence report in {domain}",
                priority="NORMAL",
                data={"report_id": report.report_id, "source": source},
            )
        return report

    def opportunity_score(self, report: IntelligenceReport) -> float:
        if report.domain not in {"MARKETS", "BUSINESS", "TECHNOLOGY", "FINANCE", "OPPORTUNITIES"}:
            return 0.0
        return round(
            report.confidence * 0.35 +
            report.impact * 0.35 +
            report.actionability * 0.30, 4
        )

    def risk_score(self, report: IntelligenceReport) -> float:
        if report.domain not in {"SECURITY", "REGULATION", "FINANCE", "POLITICS", "OPERATIONS"}:
            return 0.0
        return round(report.confidence * 0.4 + report.impact * 0.6, 4)

    def ranked_opportunities(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = [{"report_id": r.report_id, "domain": r.domain,
                 "score": self.opportunity_score(r), "summary": r.summary}
                for r in self.reports]
        return sorted(rows, key=lambda x: (-x["score"], x["report_id"]))[:limit]

    def ranked_risks(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = [{"report_id": r.report_id, "domain": r.domain,
                 "score": self.risk_score(r), "summary": r.summary}
                for r in self.reports]
        return sorted(rows, key=lambda x: (-x["score"], x["report_id"]))[:limit]

    def add_watch(self, domain: str, topic: str) -> None:
        self.watchlists.setdefault(domain.upper(), []).append(topic)

    def snapshot(self) -> dict[str, Any]:
        return {
            "domains": list(self.DOMAINS),
            "reports_total": len(self.reports),
            "opportunities": self.ranked_opportunities(),
            "risks": self.ranked_risks(),
            "watchlists": self.watchlists,
        }
