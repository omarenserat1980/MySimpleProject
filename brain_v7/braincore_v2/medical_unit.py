"""Internal cyber-medical unit: diagnosis, triage, treatment planning and recovery."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

@dataclass
class MedicalCase:
    case_id: str
    source: str
    diagnosis: str
    severity: str
    treatment: str
    status: str = "OPEN"
    evidence: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class MedicalUnit:
    DOCTORS = {
        "MED-001": "Diagnostic Doctor",
        "MED-002": "Threat/Virus Doctor",
        "MED-003": "Systems/Neural Doctor",
        "MED-004": "Treatment Doctor",
        "MED-005": "Immunity Doctor",
        "MED-006": "Laboratory Doctor",
        "MED-007": "Recovery Doctor",
        "MED-008": "Evolution Doctor",
        "MED-009": "Emergency Doctor",
        "MED-010": "Medical Director",
    }
    def __init__(self, immune_system) -> None:
        self.immune = immune_system
        self.cases: list[MedicalCase] = []
        self._counter = 0

    def _id(self) -> str:
        self._counter += 1
        return f"MEDCASE-{self._counter:06d}"

    def triage(self, source: str, evidence: dict[str, Any]) -> MedicalCase:
        severity = "LOW"
        if evidence.get("security_alert") or evidence.get("corrupted"):
            severity = "CRITICAL"
        elif evidence.get("error_rate", 0) >= 0.60:
            severity = "HIGH"
        elif evidence.get("error_rate", 0) >= 0.30:
            severity = "MEDIUM"
        diagnosis = "ANOMALY_REQUIRES_REVIEW"
        treatment = "ISOLATE_AND_DIAGNOSE" if severity in {"HIGH","CRITICAL"} else "MONITOR_AND_TEST"
        case = MedicalCase(self._id(), source, diagnosis, severity, treatment, evidence=evidence)
        self.cases.append(case)
        if severity in {"HIGH", "CRITICAL"}:
            self.immune.detect("MEDICAL_ESCALATION", source, severity, evidence)
        return case

    def diagnose(self, case_id: str) -> dict[str, Any]:
        case = next(c for c in self.cases if c.case_id == case_id)
        if case.severity == "CRITICAL":
            case.diagnosis = "CRITICAL_SECURITY_OR_CORRUPTION"
            case.treatment = "QUARANTINE_RESTORE_VERIFY"
        elif case.severity == "HIGH":
            case.diagnosis = "HIGH_RISK_BEHAVIOR_ANOMALY"
            case.treatment = "QUARANTINE_TEST_REPAIR"
        else:
            case.diagnosis = "LOWER_RISK_ANOMALY"
            case.treatment = "MONITOR_VALIDATE"
        return {"case_id": case.case_id, "diagnosis": case.diagnosis, "treatment": case.treatment}

    def treat(self, case_id: str) -> dict[str, Any]:
        case = next(c for c in self.cases if c.case_id == case_id)
        if "QUARANTINE" in case.treatment:
            self.immune.quarantine.add(case.source)
        case.status = "TREATMENT_PLANNED"
        return {"case_id": case.case_id, "status": case.status, "treatment": case.treatment}

    def recover(self, case_id: str) -> dict[str, Any]:
        case = next(c for c in self.cases if c.case_id == case_id)
        result = self.immune.recover(case.source)
        case.status = "RECOVERED"
        return {"case_id": case.case_id, "status": case.status, "recovery": result}

    def close(self, case_id: str, verification: dict[str, Any]) -> dict[str, Any]:
        case = next(c for c in self.cases if c.case_id == case_id)
        if not verification.get("passed", False):
            case.status = "REOPENED"
            return {"case_id": case.case_id, "status": case.status}
        case.status = "CLOSED"
        return {"case_id": case.case_id, "status": case.status}

    def snapshot(self) -> dict[str, Any]:
        return {
            "doctors": self.DOCTORS,
            "open_cases": sum(c.status not in {"CLOSED", "RECOVERED"} for c in self.cases),
            "cases": [c.__dict__ for c in self.cases[-100:]],
        }
