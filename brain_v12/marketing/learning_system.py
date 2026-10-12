"""Marketing learning and mastery system."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class LearningType(str, Enum):
    LESSON="LESSON"
    FRAMEWORK="FRAMEWORK"
    CASE_STUDY="CASE_STUDY"
    QUIZ="QUIZ"
    PROJECT="PROJECT"
    EXPERIMENT="EXPERIMENT"

@dataclass(frozen=True)
class LearningUnit:
    unit_id: str
    domain: str
    title: str
    kind: LearningType
    prerequisites: tuple[str, ...] = ()
    difficulty: int = 1

@dataclass(frozen=True)
class Mastery:
    domain: str
    knowledge: float
    application: float
    evidence: float
    experimentation: float

    @property
    def score(self) -> float:
        return (
            self.knowledge * .30 +
            self.application * .30 +
            self.evidence * .20 +
            self.experimentation * .20
        )

def mastery_level(score: float) -> str:
    if not 0 <= score <= 1:
        raise ValueError("score must be between 0 and 1")
    if score < .30: return "NOVICE"
    if score < .55: return "FOUNDATION"
    if score < .75: return "PRACTITIONER"
    if score < .90: return "ADVANCED"
    return "EXPERT"

def next_learning_action(mastery: Mastery) -> LearningType:
    if mastery.knowledge < .60:
        return LearningType.LESSON
    if mastery.application < .60:
        return LearningType.PROJECT
    if mastery.evidence < .60:
        return LearningType.CASE_STUDY
    if mastery.experimentation < .60:
        return LearningType.EXPERIMENT
    return LearningType.QUIZ
