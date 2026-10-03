"""Autonomous GitHub supervisor orchestration.

The supervisor coordinates the existing Planner, Agent and Task Engine. It
does not fabricate CI or domain verification; those are supplied as evidence
by the runtime.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable

@dataclass
class SupervisorEvidence:
    stage: str
    status: str
    details: dict[str, Any] = field(default_factory=dict)

@dataclass
class SupervisorSession:
    goal: str
    state: str = "PENDING"
    attempts: int = 0
    evidence: list[SupervisorEvidence] = field(default_factory=list)

    # Backward-compatible session facade used by legacy callers/tests.
    def complete(self, session: "SupervisorSession", *, ci_passed: bool, verification_passed: bool) -> "SupervisorSession":
        session.evidence.append(SupervisorEvidence("ci", "passed" if ci_passed else "failed"))
        session.evidence.append(SupervisorEvidence("verification", "passed" if verification_passed else "failed"))
        session.state = "SUCCESS" if ci_passed and verification_passed else "FAILED"
        return session

    def retry(self, session: "SupervisorSession", reason: str) -> "SupervisorSession":
        if session.state not in {"RUNNING", "FAILED"}:
            raise ValueError(f"INVALID_RETRY_STATE:{session.state}")
        session.state = "RETRYING"
        session.attempts += 1
        session.evidence.append(SupervisorEvidence("retry", "requested", {"reason": reason, "attempt": session.attempts}))
        session.state = "RUNNING"
        return session

class GitHubAutonomousSupervisor:
    TERMINAL = {"SUCCESS", "FAILED", "CANCELLED"}

    def __init__(self, agent):
        self.agent = agent

    def start(self, goal: str) -> SupervisorSession:
        return SupervisorSession(goal=goal, state="RUNNING", attempts=1)

    def record(self, session: SupervisorSession, stage: str,
               status: str, **details: Any) -> SupervisorSession:
        session.evidence.append(
            SupervisorEvidence(stage=stage, status=status, details=details)
        )
        return session

    def retry(self, session: SupervisorSession, reason: str) -> SupervisorSession:
        if session.state not in {"RUNNING", "FAILED"}:
            raise ValueError(f"INVALID_RETRY_STATE:{session.state}")
        session.state = "RETRYING"
        session.attempts += 1
        self.record(session, "retry", "requested", reason=reason,
                    attempt=session.attempts)
        session.state = "RUNNING"
        return session

    def complete(self, session: SupervisorSession, *,
                 ci_passed: bool, verification_passed: bool) -> SupervisorSession:
        self.record(session, "ci", "passed" if ci_passed else "failed")
        self.record(session, "verification",
                    "passed" if verification_passed else "failed")
        if ci_passed and verification_passed:
            session.state = "SUCCESS"
        else:
            session.state = "FAILED"
        return session

    def health(self) -> dict[str, Any]:
        return {
            "ok": True,
            "contract": "discover->authorize->execute->verify->repair->retry",
            "requires_ci_and_verification_for_success": True,
        }
