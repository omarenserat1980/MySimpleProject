"""Non-negotiable invariants for the Electronic Brain control plane."""
from __future__ import annotations


RULES = (
    "NO_SUCCESS_WITHOUT_EVIDENCE",
    "ONE_AUTHORITATIVE_ORCHESTRATOR",
    "NO_INFINITE_RETRIES",
    "HIGH_RISK_REQUIRES_APPROVAL",
    "EXECUTOR_CANNOT_SELF_VERIFY",
    "RUNTIME_EVIDENCE_SEPARATE_FROM_CI_EVIDENCE",
    "SELF_HEALING_CANNOT_SPAWN_CONTROL_LOOPS",
    "DECISIONS_MUST_BE_EXPLAINABLE",
)


class ConstitutionViolation(RuntimeError):
    pass


class BrainConstitution:
    """Central policy gate. It validates invariants; it does not execute actions."""

    def assert_success_claim(self, *, verified: bool, evidence_ids: list[str]) -> None:
        if not verified or not evidence_ids:
            raise ConstitutionViolation("success_requires_verified_evidence")

    def assert_retry(self, *, attempts: int, max_attempts: int) -> None:
        if attempts >= max_attempts:
            raise ConstitutionViolation("retry_limit_reached")

    def assert_external(self, *, risk: str, approved: bool) -> None:
        if risk in {"HIGH", "CRITICAL"} and not approved:
            raise ConstitutionViolation("approval_required_for_high_risk_action")

    def check(self) -> dict[str, object]:
        return {"ok": True, "rules": list(RULES), "orchestrator_authority": "single"}
