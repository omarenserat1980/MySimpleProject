#!/usr/bin/env python3
"""Dependency-free self-questioning engine for Brain Supervisor."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Callable, Iterable, Mapping, Optional

@dataclass
class ReflectionTurn:
    turn: int
    question: str
    answer: str = ""
    challenge: str = ""
    evidence: list[str] | None = None
    resolved: bool = False
    created_at: str = ""

    def __post_init__(self) -> None:
        if self.evidence is None:
            self.evidence = []
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

@dataclass
class ReflectionResult:
    status: str
    turns: list[ReflectionTurn]
    next_question: str | None = None

class ReflectionAgent:
    """Bounded OBSERVE -> QUESTION -> ANSWER -> CHALLENGE loop."""
    DEFAULT_QUESTIONS = (
        "What exactly am I trying to prove or accomplish?",
        "What assumption am I relying on?",
        "What evidence currently supports that assumption?",
        "What evidence would disprove it?",
        "What have I not checked yet?",
        "What independent test could expose a false success?",
        "What is the smallest safe next action?",
    )

    def __init__(self, *, max_turns: int = 7, questions: Iterable[str] | None = None):
        if max_turns < 1:
            raise ValueError("max_turns must be >= 1")
        self.max_turns = max_turns
        self.questions = tuple(questions or self.DEFAULT_QUESTIONS)
        if not self.questions:
            raise ValueError("at least one question is required")

    def first_question(self) -> str:
        return self.questions[0]

    def next_question(self, turn: int, answer: str, evidence: Iterable[str]) -> str:
        evidence = list(evidence)
        if not evidence:
            return "What concrete evidence can verify that answer?"
        if not answer.strip():
            return "What information is missing before I can answer that safely?"
        if any(x in answer.lower() for x in ("unknown", "uncertain")):
            return "What test or observation can reduce that uncertainty?"
        return self.questions[min(turn, len(self.questions) - 1)]

    def challenge(self, answer: str, evidence: Iterable[str]) -> str:
        if not answer.strip():
            return "The answer is empty; do not treat the question as resolved."
        if not list(evidence):
            return "No evidence was supplied; treat the answer as unverified."
        return "Could the supplied evidence be incomplete, stale, or unrelated to the claim?"

    def run(self, *, initial_context: Mapping[str, object] | None = None,
            answerer: Optional[Callable[[str, Mapping[str, object]], tuple[str, list[str]]]] = None) -> ReflectionResult:
        context = dict(initial_context or {})
        turns: list[ReflectionTurn] = []
        for index in range(self.max_turns):
            question = self.first_question() if index == 0 else self.next_question(
                index, turns[-1].answer, turns[-1].evidence or [])
            answer, evidence = ("", []) if answerer is None else answerer(question, context)
            evidence = [str(x) for x in evidence]
            turns.append(ReflectionTurn(
                turn=index + 1, question=question, answer=answer,
                challenge=self.challenge(answer, evidence),
                evidence=evidence, resolved=bool(answer.strip() and evidence)))
            context.update(last_question=question, last_answer=answer, last_evidence=evidence)
        status = "REFLECTION_COMPLETE" if turns and turns[-1].resolved else "REFLECTION_NEEDS_EVIDENCE"
        return ReflectionResult(status=status, turns=turns,
            next_question=self.next_question(len(turns), turns[-1].answer, turns[-1].evidence or []) if turns else None)

    @staticmethod
    def to_dict(result: ReflectionResult) -> dict[str, object]:
        return {"schema": "brain-reflection/v1", "status": result.status,
                "turns": [asdict(x) for x in result.turns], "next_question": result.next_question}

def self_test() -> None:
    agent = ReflectionAgent(max_turns=3)
    def answerer(question: str, _context: Mapping[str, object]) -> tuple[str, list[str]]:
        if question == agent.first_question():
            return "Verify the build before declaring success.", ["self_test.py", "CI result"]
        return "unknown", []
    result = agent.run(answerer=answerer)
    assert result.turns[0].resolved is True
    assert result.status == "REFLECTION_NEEDS_EVIDENCE"
    assert ReflectionAgent.to_dict(result)["schema"] == "brain-reflection/v1"

if __name__ == "__main__":
    self_test()
    print("REFLECTION_AGENT=PASS")
