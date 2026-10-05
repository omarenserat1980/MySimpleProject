from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from time import time
from uuid import uuid4
from typing import Any

from .memory import MemoryEngine, MemoryKind
from .persistent_state import SQLiteStateStore


class DecisionRisk(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    IRREVERSIBLE = "IRREVERSIBLE"


@dataclass(frozen=True)
class DecisionOption:
    option: str
    score: float
    rationale: str


@dataclass(frozen=True)
class DecisionRecord:
    decision_id: str
    subject: str
    selected: str
    alternatives: tuple[DecisionOption, ...]
    confidence: float
    risk: str
    evidence: tuple[str, ...]
    reversible: bool
    created_at: float


class DecisionEngine:
    """Evidence-aware decisions; it recommends, but cannot bypass authority gates."""

    KEY = "platform.decisions.records"

    def __init__(self, store: SQLiteStateStore, memory: MemoryEngine | None = None) -> None:
        self.store = store
        self.memory = memory or MemoryEngine(store)

    def decide(
        self,
        *,
        subject: str,
        options: list[DecisionOption],
        risk: DecisionRisk,
        confidence: float,
        evidence: list[str],
        reversible: bool = True,
    ) -> DecisionRecord:
        if not subject or not options:
            raise ValueError("subject and options are required")
        if not 0.0 <= float(confidence) <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if not evidence:
            raise ValueError("at least one evidence item is required")
        if risk is DecisionRisk.IRREVERSIBLE and reversible:
            raise ValueError("irreversible decisions cannot be marked reversible")
        if risk is DecisionRisk.IRREVERSIBLE and confidence < 0.9:
            raise ValueError("irreversible decisions require confidence >= 0.9")
        ranked = sorted(options, key=lambda item: item.score, reverse=True)
        selected = ranked[0].option
        now = time()
        record = DecisionRecord(
            decision_id=str(uuid4()),
            subject=subject,
            selected=selected,
            alternatives=tuple(ranked[1:]),
            confidence=float(confidence),
            risk=risk.value,
            evidence=tuple(evidence),
            reversible=reversible,
            created_at=now,
        )
        self.store.set(
            self.KEY,
            {**self.store.get(self.KEY, {}), record.decision_id: asdict(record)},
        )
        self.memory.remember(
            kind=MemoryKind.DECISION,
            key=subject,
            value=asdict(record),
            source="decision-engine",
            confidence=confidence,
        )
        return record

    def get(self, decision_id: str) -> DecisionRecord | None:
        value = self.store.get(self.KEY, {}).get(decision_id)
        if not value:
            return None
        return DecisionRecord(
            decision_id=value["decision_id"],
            subject=value["subject"],
            selected=value["selected"],
            alternatives=tuple(DecisionOption(**item) for item in value["alternatives"]),
            confidence=value["confidence"],
            risk=value["risk"],
            evidence=tuple(value["evidence"]),
            reversible=value["reversible"],
            created_at=value["created_at"],
        )

    def is_ready(self) -> bool:
        return self.store.is_ready() and self.memory.is_ready()


__all__ = ["DecisionEngine", "DecisionOption", "DecisionRecord", "DecisionRisk"]
