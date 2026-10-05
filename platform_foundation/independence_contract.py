"""Fail-closed contract for claiming scoped Brain independence."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class IndependenceContract:
    """Reads durable proof evidence; never grants authority from configuration alone."""

    REQUIRED_CHECKS = (
        "base_expansion_integrity",
        "real_worker_execution",
        "authority_boundary_negative_tests",
        "github_credentials_removed",
        "network_dependency_for_gate",
    )

    def __init__(self, proof_path: str | Path = "brain6_artifacts/independence_gate/independence_proof.json"):
        self.proof_path = Path(proof_path)

    def evaluate(self) -> dict[str, Any]:
        if not self.proof_path.exists():
            return {"allowed": False, "reason": "proof_missing"}

        try:
            report = json.loads(self.proof_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {"allowed": False, "reason": "proof_invalid"}

        checks = report.get("checks")
        if not isinstance(checks, dict):
            return {"allowed": False, "reason": "checks_missing"}

        missing = [name for name in self.REQUIRED_CHECKS if name not in checks]
        if missing:
            return {"allowed": False, "reason": "checks_incomplete", "missing": missing}

        failed = [
            name for name in self.REQUIRED_CHECKS
            if (
                checks[name] is not True
                if name != "network_dependency_for_gate"
                else checks[name] is not False
            )
        ]
        if failed:
            return {"allowed": False, "reason": "checks_failed", "failed": failed}

        if report.get("status") != "PROVEN_WITHIN_TEST_SCOPE":
            return {"allowed": False, "reason": "proof_status_not_proven"}

        if report.get("independence_claim_allowed") is not True:
            return {"allowed": False, "reason": "claim_not_allowed"}

        scope = report.get("scope", {})
        if scope.get("local_execution") is not True:
            return {"allowed": False, "reason": "local_execution_not_proven"}
        if scope.get("queue_to_completed") is not True:
            return {"allowed": False, "reason": "queue_completion_not_proven"}
        if scope.get("restart_recovery") is not True:
            return {"allowed": False, "reason": "restart_recovery_not_proven"}
        if scope.get("authority_boundary") is not True:
            return {"allowed": False, "reason": "authority_boundary_not_proven"}

        return {
            "allowed": True,
            "reason": "scoped_independence_proven",
            "status": report["status"],
            "scope": scope,
            "report_sha256": report.get("report_sha256"),
        }


__all__ = ["IndependenceContract"]
