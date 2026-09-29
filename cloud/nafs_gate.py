"""Decision gate that applies the Brain Nafs behavioral model.

This is an engineering control layer inspired by Quranic references. It is
not a religious authority and does not claim to create a literal soul.
"""
from dataclasses import dataclass
from .nafs_engine import NafsEngine

@dataclass(frozen=True)
class NafsGateResult:
    decision: str
    state: str
    reason: str
    quran_refs: tuple[str, ...]

class NafsGate:
    def __init__(self, engine: NafsEngine | None = None):
        self.engine = engine or NafsEngine()

    def check(
        self,
        *,
        action: str,
        benefit: float = 0.0,
        harm: float = 0.0,
        temptation: float = 0.0,
        uncertainty: float = 0.0,
        reversible: bool = True,
    ) -> NafsGateResult:
        result = self.engine.assess(
            action=action,
            benefit=benefit,
            harm=harm,
            temptation=temptation,
            uncertainty=uncertainty,
            reversible=reversible,
        )
        refs = tuple(getattr(result, "quran_references", ()))
        return NafsGateResult(
            decision=result.decision,
            state=result.state,
            reason=result.reason,
            quran_refs=refs,
        )
