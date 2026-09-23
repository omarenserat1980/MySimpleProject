"""Digital-state institutional layer for the Electronic Brain.

Models civilian/public-service functions as internal software departments.
Defensive and administrative only; no external coercive or offensive authority.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

@dataclass
class Institution:
    institution_id: str
    name: str
    function: str
    department_id: str
    manager_id: str | None = None
    objectives: list[str] = field(default_factory=list)
    active: bool = True
    metrics: dict[str, float] = field(default_factory=dict)

class DigitalState:
    INSTITUTIONS = (
        ("STATE-001","Central Administration","governance"),
        ("STATE-002","Municipal Services","municipal"),
        ("STATE-003","Health Service","health"),
        ("STATE-004","Medical Research","medical_research"),
        ("STATE-005","Education","education"),
        ("STATE-006","Science and Technology","science"),
        ("STATE-007","Economy and Finance","economy"),
        ("STATE-008","Trade and Markets","trade"),
        ("STATE-009","Transport and Logistics","transport"),
        ("STATE-010","Water and Agriculture","resources"),
        ("STATE-011","Media and Communications","media"),
        ("STATE-012","Information Intelligence","intelligence"),
        ("STATE-013","Cybersecurity","security"),
        ("STATE-014","Emergency and Civil Defense","emergency"),
        ("STATE-015","Justice and Compliance","justice"),
        ("STATE-016","Research and Development","research"),
        ("STATE-017","Environment","environment"),
        ("STATE-018","Infrastructure","infrastructure"),
        ("STATE-019","External Information Affairs","external_information"),
        ("STATE-020","Strategic Defense Simulation","defense_simulation"),
        ("STATE-021","Statistics and Planning","statistics"),
        ("STATE-022","Human Resources","human_resources"),
        ("STATE-023","Quality and Audit","audit"),
        ("STATE-024","Knowledge and Archives","knowledge"),
    )

    def __init__(self) -> None:
        self.institutions = {
            i: Institution(i, name, fn, "", objectives=[f"Operate {name} safely"])
            for i, name, fn in self.INSTITUTIONS
        }
        self.policies: dict[str, Any] = {
            "external_force": False,
            "unauthorized_access": False,
            "coercive_actions": False,
            "financial_transfer_without_authorization": False,
            "human_privacy_protection": True,
            "audit_required": True,
        }
        self.service_requests: list[dict[str, Any]] = []
        self._counter = 0

    def submit_request(self, institution_id: str, objective: str,
                        priority: str = "NORMAL") -> dict[str, Any]:
        if institution_id not in self.institutions:
            raise KeyError(institution_id)
        self._counter += 1
        req = {
            "request_id": f"REQ-{self._counter:08d}",
            "institution_id": institution_id,
            "objective": objective,
            "priority": priority,
            "status": "RECEIVED",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.service_requests.append(req)
        return req

    def update_metric(self, institution_id: str, metric: str, value: float) -> None:
        self.institutions[institution_id].metrics[metric] = max(0.0, min(1.0, float(value)))

    def dashboard(self) -> dict[str, Any]:
        return {
            "institutions": len(self.institutions),
            "active_institutions": sum(i.active for i in self.institutions.values()),
            "open_requests": sum(r["status"] != "CLOSED" for r in self.service_requests),
            "policy_guardrails": self.policies,
            "institution_metrics": {
                i.institution_id: i.metrics for i in self.institutions.values()
            },
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "institutions": [i.__dict__ for i in self.institutions.values()],
            "requests": self.service_requests[-100:],
            "dashboard": self.dashboard(),
        }
