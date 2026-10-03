"""Autonomous GitHub Actions supervisor decision engine."""
from __future__ import annotations
from dataclasses import dataclass
from .github_failure_diagnoser import diagnose, FailureDiagnosis

@dataclass(frozen=True)
class SupervisorDecision:
    action: str
    diagnosis: FailureDiagnosis
    automatic: bool

class GitHubActionsSupervisor:
    def decide(self, job: dict, logs: str = "") -> SupervisorDecision:
        d = diagnose(job, logs)
        if d.retryable:
            return SupervisorDecision("rerun_failed_jobs", d, True)
        if d.repair == "inspect_and_patch":
            return SupervisorDecision("diagnose_then_patch", d, False)
        return SupervisorDecision(d.repair, d, False)

    def can_auto_repair(self, decision: SupervisorDecision) -> bool:
        return decision.automatic and decision.action == "rerun_failed_jobs"
