"""Adaptive reasoning engine for the Electronic Brain.

Improves understanding, reasoning and flexibility without pretending to be a
general-purpose foundation model. It builds a structured interpretation of an
objective, generates multiple hypotheses, tests contradictions, estimates
uncertainty, and selects a reversible next strategy.

Safety: this module only produces internal reasoning artifacts. It never
executes external side effects, handles credentials, moves money, or makes
irreversible commitments.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import exp
from typing import Any, Iterable, Mapping


@dataclass
class Interpretation:
    text: str
    intent: str
    entities: list[str]
    constraints: list[str]
    ambiguities: list[str]
    assumptions: list[str]
    confidence: float


@dataclass
class Hypothesis:
    label: str
    interpretation: str
    rationale: str
    evidence_for: list[str] = field(default_factory=list)
    evidence_against: list[str] = field(default_factory=list)
    confidence: float = 0.5
    reversibility: float = 1.0


@dataclass
class ReasoningResult:
    interpretation: Interpretation
    hypotheses: list[Hypothesis]
    contradictions: list[str]
    unknowns: list[str]
    selected_strategy: str
    confidence: float
    flexibility_score: float
    reasoning_trace: list[str]


class AdaptiveReasoningEngine:
    """A deterministic, inspectable reasoning layer.

    The engine deliberately separates:
      1. understanding the request,
      2. generating competing explanations/plans,
      3. testing evidence and contradictions,
      4. selecting a reversible strategy,
      5. retaining alternatives for replanning.
    """

    INTENTS = (
        "BUILD", "IMPROVE", "ANALYZE", "CREATE", "OPERATE",
        "LEARN", "DECIDE", "DEBUG", "UNKNOWN",
    )

    def __init__(self, *, minimum_confidence: float = 0.55) -> None:
        self.minimum_confidence = max(0.0, min(1.0, float(minimum_confidence)))
        self.history: list[dict[str, Any]] = []
        self._cycle = 0

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return [t.strip(".,!?;:()[]{}\"'").lower()
                for t in str(text).split() if t.strip()]

    def understand(
        self,
        objective: str,
        *,
        context: Mapping[str, Any] | None = None,
        constraints: Iterable[str] = (),
    ) -> Interpretation:
        text = str(objective).strip()
        tokens = self._tokens(text)
        lower = text.lower()
        context = context or {}
        explicit = [str(x) for x in constraints if str(x).strip()]

        intent = "UNKNOWN"
        keyword_map = {
            "BUILD": ("build", "create", "develop", "construct", "implement", "بن", "طور", "أنشئ"),
            "IMPROVE": ("improve", "upgrade", "enhance", "optimize", "طور", "حسن"),
            "ANALYZE": ("analyze", "analyse", "inspect", "compare", "حلل", "قارن"),
            "CREATE": ("generate", "design", "make", "produce", "أنشئ", "ولد", "اصنع"),
            "OPERATE": ("run", "deploy", "publish", "operate", "شغل", "انشر", "نفذ"),
            "LEARN": ("learn", "study", "understand", "تعلم", "افهم"),
            "DECIDE": ("decide", "choose", "select", "قرر", "اختر"),
            "DEBUG": ("debug", "fix", "error", "repair", "أصلح", "خطأ"),
        }
        for candidate, words in keyword_map.items():
            if any(w in lower for w in words):
                intent = candidate
                break

        ambiguities: list[str] = []
        if len(tokens) < 3:
            ambiguities.append("objective_is_short")
        if any(x in lower for x in ("it", "this", "that", "هذا", "ذلك", "هو")):
            ambiguities.append("referent_needs_context")
        if not explicit and any(x in lower for x in ("all", "everything", "كل", "الجميع")):
            ambiguities.append("scope_is_broad")

        assumptions = [
            "external side effects require explicit authorization",
            "unknown facts remain unknown until evidence is available",
        ]
        if context:
            assumptions.append("available context may refine the interpretation")

        entity_candidates = [
            t for t in tokens
            if len(t) > 3 and t not in {
                "want", "need", "make", "build", "develop", "improve",
                "أريد", "أريد", "طور", "العقل", "من", "ناحية",
            }
        ][:20]

        confidence = 0.72
        confidence -= 0.08 * len(ambiguities)
        if context:
            confidence += 0.05
        if explicit:
            confidence += 0.08
        confidence = self._clamp(confidence)

        return Interpretation(
            text=text,
            intent=intent,
            entities=entity_candidates,
            constraints=explicit,
            ambiguities=ambiguities,
            assumptions=assumptions,
            confidence=confidence,
        )

    def generate_hypotheses(
        self,
        interpretation: Interpretation,
        *,
        evidence: Iterable[str] = (),
    ) -> list[Hypothesis]:
        ev = [str(x) for x in evidence if str(x).strip()]
        base = interpretation.text or "the current objective"
        hypotheses = [
            Hypothesis(
                "DIRECT",
                base,
                "Use the most direct interpretation of the objective.",
                evidence_for=ev[:3],
                confidence=interpretation.confidence,
                reversibility=0.90,
            ),
            Hypothesis(
                "DECOMPOSE",
                f"Break {base!r} into smaller measurable stages.",
                "Decomposition reduces ambiguity and makes failures recoverable.",
                evidence_for=["complex objectives benefit from staged execution"],
                confidence=self._clamp(interpretation.confidence + 0.04),
                reversibility=0.98,
            ),
            Hypothesis(
                "EXPERIMENT",
                f"Run a small reversible experiment before committing to {base!r}.",
                "Testing uncertain assumptions preserves flexibility.",
                evidence_for=["uncertainty favors reversible experiments"],
                confidence=self._clamp(interpretation.confidence + 0.02),
                reversibility=1.00,
            ),
        ]
        if interpretation.ambiguities:
            hypotheses.append(Hypothesis(
                "CLARIFY_BY_EVIDENCE",
                f"Resolve ambiguity around {base!r} using available evidence first.",
                "Ambiguous objectives should not be converted into irreversible actions.",
                evidence_for=["ambiguity detected"],
                confidence=self._clamp(interpretation.confidence - 0.03),
                reversibility=1.00,
            ))
        return hypotheses

    def test_hypotheses(
        self,
        hypotheses: list[Hypothesis],
        *,
        observations: Iterable[Mapping[str, Any]] = (),
    ) -> tuple[list[Hypothesis], list[str], list[str]]:
        contradictions: list[str] = []
        unknowns: list[str] = []
        obs = list(observations)

        for item in hypotheses:
            for row in obs:
                statement = str(row.get("statement", "")).strip()
                polarity = str(row.get("polarity", "support")).lower()
                if not statement:
                    continue
                if polarity in {"against", "contradiction", "false"}:
                    item.evidence_against.append(statement)
                    item.confidence -= 0.12
                    contradictions.append(f"{item.label}: {statement}")
                else:
                    item.evidence_for.append(statement)
                    item.confidence += 0.06
            if not item.evidence_for and not item.evidence_against:
                unknowns.append(f"{item.label}: insufficient evidence")
            item.confidence = self._clamp(item.confidence)

        return hypotheses, contradictions, unknowns

    def select_strategy(self, hypotheses: list[Hypothesis]) -> tuple[str, float]:
        if not hypotheses:
            return "GATHER_EVIDENCE", 0.0
        ranked = sorted(
            hypotheses,
            key=lambda h: (
                h.confidence * 0.65 + h.reversibility * 0.35,
                h.reversibility,
            ),
            reverse=True,
        )
        best = ranked[0]
        return best.label, self._clamp(best.confidence * 0.65 + best.reversibility * 0.35)

    def reason(
        self,
        objective: str,
        *,
        context: Mapping[str, Any] | None = None,
        constraints: Iterable[str] = (),
        evidence: Iterable[str] = (),
        observations: Iterable[Mapping[str, Any]] = (),
    ) -> ReasoningResult:
        self._cycle += 1
        interpretation = self.understand(objective, context=context, constraints=constraints)
        hypotheses = self.generate_hypotheses(interpretation, evidence=evidence)
        hypotheses, contradictions, unknowns = self.test_hypotheses(
            hypotheses, observations=observations
        )
        strategy, confidence = self.select_strategy(hypotheses)

        alternative_count = max(0, len(hypotheses) - 1)
        flexibility = self._clamp(
            0.50
            + 0.15 * min(alternative_count, 3)
            + 0.20 * interpretation.confidence
            + 0.15 * min(h.reversibility for h in hypotheses)
            - 0.08 * min(len(contradictions), 3)
        )
        trace = [
            "parse objective",
            f"identify intent={interpretation.intent}",
            f"generate {len(hypotheses)} competing hypotheses",
            f"test evidence: {len(list(observations))} observations",
            f"select reversible strategy={strategy}",
            "retain alternatives for replanning",
        ]
        result = ReasoningResult(
            interpretation=interpretation,
            hypotheses=hypotheses,
            contradictions=contradictions,
            unknowns=unknowns,
            selected_strategy=strategy,
            confidence=confidence,
            flexibility_score=flexibility,
            reasoning_trace=trace,
        )
        self.history.append(asdict(result))
        self.history = self.history[-100:]
        return result

    def snapshot(self) -> dict[str, Any]:
        return {
            "engine": "AdaptiveReasoningEngine",
            "cycles": self._cycle,
            "minimum_confidence": self.minimum_confidence,
            "history_size": len(self.history),
            "last_result": self.history[-1] if self.history else None,
            "safety": {
                "internal_reasoning_only": True,
                "external_side_effects": False,
                "credential_access": False,
                "money_movement": False,
            },
        }
