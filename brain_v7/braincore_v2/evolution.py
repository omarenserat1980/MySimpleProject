"""Post-V1000 expansion layer.

This module provides lightweight, composable primitives for the roadmap:
adaptive cognition, research, engineering tasks, multi-agent coordination,
long-horizon goals, multimodal events, self-model, and runtime evolution.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GoalNode:
    id: str
    description: str
    priority: float = 0.5
    status: str = "PENDING"
    parent_id: str | None = None
    children: list[str] = field(default_factory=list)


class AdaptiveGoalManager:
    def __init__(self):
        self.goals: dict[str, GoalNode] = {}

    def add(self, goal: GoalNode):
        self.goals[goal.id] = goal

    def decompose(self, goal_id: str, descriptions: list[str]):
        goal = self.goals[goal_id]
        for i, description in enumerate(descriptions, 1):
            child_id = f"{goal_id}.{i}"
            self.add(GoalNode(child_id, description, goal.priority, parent_id=goal_id))
            goal.children.append(child_id)
        goal.status = "DECOMPOSED"
        return [self.goals[x] for x in goal.children]


@dataclass
class Evidence:
    source: str
    claim: str
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)


class ResearchMemory:
    def __init__(self):
        self.evidence: list[Evidence] = []

    def add(self, evidence: Evidence):
        self.evidence.append(evidence)

    def search(self, text: str):
        terms = set(text.lower().split())
        return [e for e in self.evidence if terms & set(e.claim.lower().split())]


@dataclass
class EngineeringTask:
    id: str
    objective: str
    phase: str = "INSPECT"
    attempts: int = 0
    result: Any = None


class EngineeringLoop:
    PHASES = ("INSPECT", "PLAN", "IMPLEMENT", "EXECUTE", "OBSERVE", "REPAIR", "COMPLETE")

    def advance(self, task: EngineeringTask, result: Any = None):
        task.attempts += 1
        task.result = result
        index = self.PHASES.index(task.phase)
        if index < len(self.PHASES) - 1:
            task.phase = self.PHASES[index + 1]
        return task


@dataclass
class AgentMessage:
    sender: str
    receiver: str
    kind: str
    payload: dict[str, Any]


class MultiAgentBus:
    def __init__(self):
        self.messages: list[AgentMessage] = []

    def send(self, message: AgentMessage):
        self.messages.append(message)

    def receive(self, receiver: str):
        return [m for m in self.messages if m.receiver == receiver]


@dataclass
class SelfModel:
    capabilities: set[str] = field(default_factory=set)
    limitations: set[str] = field(default_factory=set)
    resources: dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0

    def capability(self, name: str, confidence: float = 0.5):
        self.capabilities.add(name)
        self.confidence = max(self.confidence, confidence)


class EvolutionRegistry:
    def __init__(self):
        self.modules: dict[str, Any] = {}
        self.versions: list[str] = ["V9.3"]

    def register(self, name: str, module: Any):
        self.modules[name] = module

    def advance(self, version: str):
        if version not in self.versions:
            self.versions.append(version)

    def status(self):
        return {
            "latest_declared_version": self.versions[-1],
            "modules": sorted(self.modules),
        }
