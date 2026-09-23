"""Unified operational snapshot for dashboards and audits."""
from __future__ import annotations
from typing import Any
from .operational_control_plane import OperationalControlPlane
from .job_lifecycle import JobLifecycle


class OperationsDashboard:
    def __init__(self, control: OperationalControlPlane | None = None, jobs: JobLifecycle | None = None):
        self.control = control or OperationalControlPlane()
        self.jobs = jobs or JobLifecycle()

    def snapshot(self, *, brain: dict[str, Any], readiness: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "brain_cycle": brain.get("cycle"),
            "objective": brain.get("objective"),
            "focus": brain.get("selected_internal_focus"),
            "organization": brain.get("organization", {}),
            "external_work": brain.get("external_work", {}),
            "external_work_metrics": brain.get("external_work_metrics", {}),
            "control_plane": self.control.snapshot(),
            "jobs": self.jobs.snapshot(),
            "readiness": readiness or brain.get("completion_report", {}),
            "safety": {
                "external_side_effects": False,
                "money_movement": False,
                "credential_storage": False,
                "requires_user_for_external_side_effects": True,
            },
        }
