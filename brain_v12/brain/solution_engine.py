"""Deterministic, evidence-first selection and fallback for solution options.

The engine only invokes callbacks explicitly supplied by its caller. It does not
discover services or make network, financial, or other external requests itself.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Callable, Iterable, Mapping
from uuid import uuid4


class SourceType(str, Enum):
    BUILT_IN = "built_in"
    OPEN_SOURCE = "open_source"
    EXPERT = "expert"
    SERVICE = "service"


@dataclass(frozen=True)
class Problem:
    description: str
    required_capabilities: tuple[str, ...] = ()
    platform: str | None = None
    max_cost: float = 0
    allow_paid: bool = False


class ProblemAnalyzer:
    """Normalize user requirements into a stable, explicit problem contract."""

    def analyze(self, value: str | Mapping[str, Any] | Problem) -> Problem:
        if isinstance(value, Problem):
            problem = Problem(
                description=str(value.description).strip(),
                required_capabilities=tuple(sorted({str(x).strip().lower() for x in value.required_capabilities if str(x).strip()})),
                platform=str(value.platform).strip().lower() if value.platform else None,
                max_cost=max(0.0, float(value.max_cost)),
                allow_paid=bool(value.allow_paid),
            )
        elif isinstance(value, Mapping):
            problem = Problem(
                description=str(value.get("description", "")).strip(),
                required_capabilities=tuple(sorted({str(x).strip().lower() for x in value.get("required_capabilities", ()) if str(x).strip()})),
                platform=str(value["platform"]).strip().lower() if value.get("platform") else None,
                max_cost=max(0.0, float(value.get("max_cost", 0))),
                allow_paid=bool(value.get("allow_paid", False)),
            )
        else:
            problem = Problem(description=str(value or "").strip())
        if not problem.description:
            raise ValueError("problem description is required")
        if not problem.allow_paid and problem.max_cost != 0:
            problem = Problem(problem.description, problem.required_capabilities,
                              problem.platform, 0, False)
        return problem


@dataclass(frozen=True)
class Alternative:
    id: str
    name: str
    source_type: SourceType | str = SourceType.BUILT_IN
    cost: float = 0
    capabilities: tuple[str, ...] = ()
    platforms: tuple[str, ...] = ()
    security_approved: bool | None = None
    risk: str = "low"
    quality: float = 0.5
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self, "source_type", SourceType(self.source_type))
        if self.security_approved is None:
            object.__setattr__(self, "security_approved",
                               self.source_type == SourceType.BUILT_IN)
        if not self.id.strip() or not self.name.strip():
            raise ValueError("alternative id and name are required")
        if self.cost < 0:
            raise ValueError("alternative cost cannot be negative")


class AlternativeRegistry:
    def __init__(self, alternatives: Iterable[Alternative] = ()):
        self._items: dict[str, Alternative] = {}
        for alternative in alternatives:
            self.register(alternative)

    def register(self, alternative: Alternative) -> Alternative:
        if alternative.id in self._items:
            raise ValueError(f"duplicate alternative id: {alternative.id}")
        self._items[alternative.id] = alternative
        return alternative

    def get(self, alternative_id: str) -> Alternative | None:
        return self._items.get(alternative_id)

    def list(self) -> list[Alternative]:
        return list(self._items.values())


class SolutionEngine:
    """Select, execute, verify, and audit candidates through a bounded fallback chain."""

    def __init__(self, registry: AlternativeRegistry | None = None,
                 analyzer: ProblemAnalyzer | None = None, max_attempts: int = 3):
        self.registry = registry or AlternativeRegistry()
        self.analyzer = analyzer or ProblemAnalyzer()
        self.max_attempts = max(1, int(max_attempts))

    @staticmethod
    def _compatibility(problem: Problem, alternative: Alternative) -> tuple[bool, str]:
        missing = set(problem.required_capabilities) - {x.lower() for x in alternative.capabilities}
        if missing:
            return False, "missing_capabilities:" + ",".join(sorted(missing))
        if problem.platform and alternative.platforms and problem.platform not in {x.lower() for x in alternative.platforms}:
            return False, "platform_mismatch"
        return True, "compatible"

    def rank(self, problem: Problem | Mapping[str, Any] | str) -> tuple[Problem, list[Alternative], list[dict[str, str]]]:
        analyzed = self.analyzer.analyze(problem)
        eligible, rejected = [], []
        for item in self.registry.list():
            compatible, reason = self._compatibility(analyzed, item)
            if not compatible:
                rejected.append({"alternative_id": item.id, "check": "compatibility", "reason": reason})
            elif not item.security_approved or item.risk.lower() in {"critical", "blocked"}:
                rejected.append({"alternative_id": item.id, "check": "security", "reason": "security_not_approved"})
            elif item.cost > analyzed.max_cost or (item.cost > 0 and not analyzed.allow_paid):
                rejected.append({"alternative_id": item.id, "check": "cost", "reason": "cost_not_allowed"})
            else:
                eligible.append(item)
        # Free options win when suitable; ties resolve deterministically.
        eligible.sort(key=lambda x: (x.cost > 0, x.cost, -x.quality,
                                     x.source_type.value, x.id))
        return analyzed, eligible, rejected

    def solve(self, problem: Problem | Mapping[str, Any] | str,
              executors: Mapping[str, Callable[[Problem, Alternative], Any]],
              verifier: Callable[[Any, Problem, Alternative], Any]) -> dict[str, Any]:
        analyzed, candidates, rejected = self.rank(problem)
        fallback_chain = candidates[:self.max_attempts]
        run_id = "SOL-" + uuid4().hex[:12]
        audit: list[dict[str, Any]] = [{"event": "ANALYZED", "problem": asdict(analyzed)}]
        attempts = []
        if len(candidates) > len(fallback_chain):
            audit.append({"event": "FALLBACK_LIMIT_REACHED",
                          "deferred_count": len(candidates) - len(fallback_chain)})
        for alternative in fallback_chain:
            executor = executors.get(alternative.id)
            if executor is None:
                rejected.append({"alternative_id": alternative.id, "check": "execution", "reason": "executor_unavailable"})
                audit.append({"event": "SKIPPED", "alternative_id": alternative.id, "reason": "executor_unavailable"})
                continue
            attempt = {"alternative_id": alternative.id, "source_type": alternative.source_type.value,
                       "status": "RUNNING"}
            audit.append({"event": "EXECUTION_STARTED", "alternative_id": alternative.id})
            try:
                output = executor(analyzed, alternative)
                attempt["execution"] = "SUCCEEDED"
            except Exception as exc:  # fallback is intentional and bounded by registry size
                attempt.update(status="FAILED", error=f"{type(exc).__name__}: {exc}")
                attempts.append(attempt)
                audit.append({"event": "EXECUTION_FAILED", "alternative_id": alternative.id,
                              "error": attempt["error"]})
                continue
            try:
                verified = verifier(output, analyzed, alternative)
                passed = (isinstance(verified, Mapping) and verified.get("ok") is True
                          and bool(verified.get("evidence_ref") or verified.get("evidence")))
            except Exception as exc:
                verified, passed = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}, False
            evidence = (verified.get("evidence_ref") or verified.get("evidence")
                        if isinstance(verified, Mapping) else None)
            attempt.update(status="VERIFIED" if passed else "UNVERIFIED",
                           verification=verified, evidence=evidence)
            attempts.append(attempt)
            audit.append({"event": "VERIFICATION_PASSED" if passed else "VERIFICATION_FAILED",
                          "alternative_id": alternative.id, "evidence": evidence})
            if passed:
                evidence_ref = str(evidence)
                audit.append({"event": "COMPLETED", "alternative_id": alternative.id,
                              "evidence_ref": evidence_ref})
                return {"ok": True, "status": "VERIFIED", "run_id": run_id,
                        "problem": asdict(analyzed), "selected": alternative.id,
                        "fallback_chain": [x.id for x in fallback_chain], "attempts": attempts,
                        "rejected": rejected, "evidence_ref": evidence_ref, "audit": audit}
        audit.append({"event": "FAILED", "reason": "no_candidate_verified"})
        return {"ok": False, "status": "FAILED", "run_id": run_id,
                "problem": asdict(analyzed), "selected": None,
                "fallback_chain": [x.id for x in fallback_chain], "attempts": attempts,
                "rejected": rejected, "evidence_ref": f"audit://{run_id}/failure", "audit": audit}
