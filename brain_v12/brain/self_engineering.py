"""Evidence-gated self-engineering workflow for Electronic Brain V12.

This module coordinates engineering decisions; it deliberately does not execute
shell commands, mutate source files, deploy services, or claim live capability.
Adapters must supply observed evidence and enforce their own authorization.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any, Iterable
from uuid import uuid4


class RunState(str, Enum):
    DRAFT = "DRAFT"
    INSPECTING = "INSPECTING"
    PLANNED = "PLANNED"
    AUTHORIZED = "AUTHORIZED"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    VERIFIED = "VERIFIED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


class EvidenceKind(str, Enum):
    SOURCE_INSPECTION = "source_inspection"
    TEST_RESULT = "test_result"
    RUNTIME_PROBE = "runtime_probe"
    HUMAN_APPROVAL = "human_approval"
    DEPLOYMENT = "deployment"


@dataclass(frozen=True)
class Evidence:
    kind: str
    claim: str
    outcome: str
    source: str
    observed_at: str
    details: dict[str, Any] = field(default_factory=dict)
    digest: str = ""

    def _canonical_payload(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "claim": self.claim,
            "outcome": self.outcome,
            "source": self.source,
            "observed_at": self.observed_at,
            "details": self.details,
        }

    def verify_digest(self) -> bool:
        """Recompute the digest so changed evidence cannot be accepted silently."""
        canonical = json.dumps(
            self._canonical_payload(), ensure_ascii=False, sort_keys=True,
            separators=(",", ":"),
        )
        expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return bool(self.digest) and hashlib.compare_digest(self.digest, expected)

    @classmethod
    def create(
        cls, kind: EvidenceKind | str, claim: str, outcome: str,
        source: str, details: dict[str, Any] | None = None,
    ) -> "Evidence":
        payload = {
            "kind": kind.value if isinstance(kind, EvidenceKind) else str(kind),
            "claim": claim,
            "outcome": outcome,
            "source": source,
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "details": details or {},
        }
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return cls(**payload, digest=hashlib.sha256(canonical.encode("utf-8")).hexdigest())


@dataclass
class EngineeringRun:
    goal: str
    run_id: str = field(default_factory=lambda: str(uuid4()))
    state: RunState = RunState.DRAFT
    plan: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    changes_authorized: bool = False

    def add_evidence(self, evidence: Evidence) -> None:
        if not evidence.digest:
            raise ValueError("EVIDENCE_DIGEST_REQUIRED")
        if not evidence.verify_digest():
            raise ValueError("EVIDENCE_DIGEST_MISMATCH")
        self.evidence.append(evidence)

    def report(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "goal": self.goal,
            "state": self.state.value,
            "plan": list(self.plan),
            "blockers": list(self.blockers),
            "changes_authorized": self.changes_authorized,
            "evidence_count": len(self.evidence),
            "evidence": [asdict(item) for item in self.evidence],
            "claims": self.claims(),
        }

    def claims(self) -> dict[str, bool]:
        return {
            "source_inspected": self._has(EvidenceKind.SOURCE_INSPECTION, "passed"),
            "tests_passed": self._has(EvidenceKind.TEST_RESULT, "passed"),
            "runtime_verified": self._has(EvidenceKind.RUNTIME_PROBE, "passed"),
            "deployment_verified": self._has(EvidenceKind.DEPLOYMENT, "passed"),
        }

    def _has(self, kind: EvidenceKind, outcome: str) -> bool:
        return any(
            e.verify_digest() and e.kind == kind.value and e.outcome.lower() == outcome
            for e in self.evidence
        )


class SelfEngineeringEngine:
    """A conservative, evidence-first coordinator for an engineering run."""

    def start(self, goal: str) -> EngineeringRun:
        if not goal or not goal.strip():
            raise ValueError("GOAL_REQUIRED")
        return EngineeringRun(goal=goal.strip(), state=RunState.INSPECTING)

    def record_inspection(
        self, run: EngineeringRun, *, source: str, findings: Iterable[str],
        details: dict[str, Any] | None = None,
    ) -> EngineeringRun:
        findings_list = [str(item).strip() for item in findings if str(item).strip()]
        inspection_ok = bool(source and source.strip() and findings_list)
        run.add_evidence(Evidence.create(
            EvidenceKind.SOURCE_INSPECTION,
            "Repository/source inspection completed",
            "passed" if inspection_ok else "failed",
            source.strip() if source and source.strip() else "unspecified",
            {"findings": findings_list, **(details or {})},
        ))
        run.plan = [
            "Confirm current source and runtime authority",
            "Reproduce the target problem with a bounded test",
            "Prepare the smallest reversible change",
            "Run targeted tests and relevant regression tests",
            "Review evidence and report verified, failed, or blocked",
        ]
        if inspection_ok:
            run.state = RunState.PLANNED
            run.blockers = [b for b in run.blockers if b != "SOURCE_INSPECTION_INCOMPLETE"]
        else:
            run.state = RunState.BLOCKED
            if "SOURCE_INSPECTION_INCOMPLETE" not in run.blockers:
                run.blockers.append("SOURCE_INSPECTION_INCOMPLETE")
        return run

    def authorize_changes(self, run: EngineeringRun, *, approved: bool, scope: str = "") -> EngineeringRun:
        if not approved:
            run.changes_authorized = False
            run.blockers.append("SOURCE_MUTATION_NOT_AUTHORIZED")
            run.state = RunState.BLOCKED
            return run
        if not scope.strip():
            raise ValueError("AUTHORIZATION_SCOPE_REQUIRED")
        run.changes_authorized = True
        run.add_evidence(Evidence.create(
            EvidenceKind.HUMAN_APPROVAL, "Source mutation authorized", "passed",
            "explicit_user_approval", {"scope": scope.strip()},
        ))
        run.state = RunState.AUTHORIZED
        return run

    def begin_execution(self, run: EngineeringRun) -> EngineeringRun:
        if not run.changes_authorized:
            run.blockers.append("SOURCE_MUTATION_NOT_AUTHORIZED")
            run.state = RunState.BLOCKED
            return run
        if run.state != RunState.AUTHORIZED:
            raise ValueError(f"INVALID_EXECUTION_STATE:{run.state.value}")
        run.state = RunState.EXECUTING
        return run

    def record_test_result(
        self, run: EngineeringRun, *, passed: bool, source: str,
        details: dict[str, Any] | None = None,
    ) -> EngineeringRun:
        run.add_evidence(Evidence.create(
            EvidenceKind.TEST_RESULT, "Targeted engineering tests",
            "passed" if passed else "failed", source,
            details or {},
        ))
        run.state = RunState.VERIFYING if passed else RunState.FAILED
        if not passed:
            run.blockers.append("TESTS_FAILED")
        return run

    def record_runtime_probe(
        self, run: EngineeringRun, *, passed: bool, source: str,
        details: dict[str, Any] | None = None,
    ) -> EngineeringRun:
        run.add_evidence(Evidence.create(
            EvidenceKind.RUNTIME_PROBE, "Live runtime behavior",
            "passed" if passed else "failed", source, details or {},
        ))
        if not passed:
            run.blockers.append("RUNTIME_PROBE_FAILED")
            run.state = RunState.FAILED
        return run

    def finalize(self, run: EngineeringRun, *, runtime_required: bool = False) -> EngineeringRun:
        claims = run.claims()
        if not claims["tests_passed"]:
            run.state = RunState.BLOCKED if not any(e.kind == EvidenceKind.TEST_RESULT.value for e in run.evidence) else RunState.FAILED
            if "PASSING_TEST_EVIDENCE_REQUIRED" not in run.blockers:
                run.blockers.append("PASSING_TEST_EVIDENCE_REQUIRED")
            return run
        if runtime_required and not claims["runtime_verified"]:
            run.state = RunState.BLOCKED
            if "LIVE_RUNTIME_EVIDENCE_REQUIRED" not in run.blockers:
                run.blockers.append("LIVE_RUNTIME_EVIDENCE_REQUIRED")
            return run
        run.state = RunState.VERIFIED
        return run
