"""Cyber immune system for the Electronic Brain.

Defensive only: detects anomalies, quarantines affected workers/tasks,
recovers from known-good state, and records incidents. It never performs
offensive actions against external systems.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

@dataclass
class ImmuneIncident:
    incident_id: str
    kind: str
    severity: str
    source: str
    evidence: dict[str, Any]
    status: str = "DETECTED"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class CyberImmuneSystem:
    SEVERITY = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}

    def __init__(self, organization=None) -> None:
        self.organization = organization
        self.incidents: list[ImmuneIncident] = []
        self.quarantine: set[str] = set()
        self.trusted_snapshots: dict[str, dict[str, Any]] = {}
        self._counter = 0

    def _id(self) -> str:
        self._counter += 1
        return f"IMMUNE-{self._counter:06d}"

    def baseline(self, component_id: str, state: dict[str, Any]) -> None:
        self.trusted_snapshots[component_id] = dict(state)

    def detect(self, kind: str, source: str, severity: str = "MEDIUM",
               evidence: dict[str, Any] | None = None) -> ImmuneIncident:
        severity = severity.upper()
        if severity not in self.SEVERITY:
            severity = "MEDIUM"
        incident = ImmuneIncident(
            self._id(), kind, severity, source, evidence or {}
        )
        self.incidents.append(incident)
        if self.SEVERITY[severity] >= self.SEVERITY["HIGH"]:
            self.quarantine.add(source)
            incident.status = "QUARANTINED"
        return incident

    def scan_employee(self, employee) -> ImmuneIncident | None:
        if employee.status == "RETIRED":
            return None
        total = employee.completed_tasks + employee.failed_tasks
        if total >= 10:
            failure_rate = employee.failed_tasks / total
            if failure_rate >= 0.60:
                return self.detect(
                    "BEHAVIOR_ANOMALY", employee.employee_id, "HIGH",
                    {"failure_rate": round(failure_rate, 4), "tasks": total}
                )
        return None

    def scan_task_result(self, task_id: str, result: Any) -> ImmuneIncident | None:
        if isinstance(result, dict):
            error = str(result.get("error", "")).lower()
            if error or result.get("status") in {"ERROR", "CORRUPTED", "SECURITY_ALERT"}:
                return self.detect(
                    "TASK_ANOMALY", task_id, "HIGH",
                    {"result": result}
                )
        return None

    def recover(self, source: str) -> dict[str, Any]:
        self.quarantine.discard(source)
        incident = next((i for i in reversed(self.incidents) if i.source == source), None)
        if incident:
            incident.status = "RECOVERED"
        return {
            "source": source,
            "recovered": True,
            "baseline_available": source in self.trusted_snapshots,
        }

    def health(self) -> dict[str, Any]:
        active = [i for i in self.incidents if i.status in {"DETECTED", "QUARANTINED"}]
        return {
            "status": "DEGRADED" if active else "HEALTHY",
            "active_incidents": len(active),
            "quarantined": sorted(self.quarantine),
            "incidents_total": len(self.incidents),
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "health": self.health(),
            "incidents": [i.__dict__ for i in self.incidents[-100:]],
            "trusted_baselines": list(self.trusted_snapshots),
        }
