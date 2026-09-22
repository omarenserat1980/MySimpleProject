"""Integrated V2000 orchestration layer.

Implements the roadmap primitives as one bounded runtime:
goals -> research -> engineering -> agents -> self-model -> evolution.
It does not claim consciousness and keeps host/system execution outside this layer.
"""
from dataclasses import dataclass, field
from typing import Any
from .evolution import (
    GoalNode, Evidence, EngineeringTask, AgentMessage, SelfModel,
    AdaptiveGoalManager, ResearchMemory, EngineeringLoop, MultiAgentBus,
    EvolutionRegistry,
)

@dataclass
class BrainState:
    cycle: int = 0
    active_goal: str | None = None
    last_result: Any = None
    history: list[dict] = field(default_factory=list)

class V2000Brain:
    def __init__(self):
        self.goals = AdaptiveGoalManager()
        self.research = ResearchMemory()
        self.engineering = EngineeringLoop()
        self.agents = MultiAgentBus()
        self.self_model = SelfModel()
        self.registry = EvolutionRegistry()
        self.state = BrainState()
        self._register_core()

    def _register_core(self):
        for name, module in {
            "goal_manager": self.goals,
            "research_memory": self.research,
            "engineering_loop": self.engineering,
            "multi_agent_bus": self.agents,
            "self_model": self.self_model,
        }.items():
            self.registry.register(name, module)
        for v in ("V1001","V1100","V1200","V1300","V1400","V1500",
                  "V1600","V1700","V1800","V1900","V2000"):
            self.registry.advance(v)

    def create_goal(self, goal_id: str, description: str, priority: float = 0.5):
        goal = GoalNode(goal_id, description, priority)
        self.goals.add(goal)
        self.state.active_goal = goal_id
        return goal

    def decompose_goal(self, goal_id: str, parts: list[str]):
        return self.goals.decompose(goal_id, parts)

    def remember_evidence(self, source: str, claim: str, confidence: float):
        item = Evidence(source, claim, max(0.0, min(1.0, confidence)))
        self.research.add(item)
        return item

    def start_engineering(self, task_id: str, objective: str):
        return EngineeringTask(task_id, objective)

    def advance_engineering(self, task: EngineeringTask, result: Any = None):
        return self.engineering.advance(task, result)

    def send_agent_message(self, sender: str, receiver: str, kind: str, payload: dict):
        msg = AgentMessage(sender, receiver, kind, payload)
        self.agents.send(msg)
        return msg

    def update_self_model(self, capability: str, confidence: float = 0.5):
        self.self_model.capability(capability, confidence)
        return self.self_model

    def cycle(self, result: Any = None):
        self.state.cycle += 1
        self.state.last_result = result
        snapshot = {
            "cycle": self.state.cycle,
            "active_goal": self.state.active_goal,
            "result": result,
            "registered_modules": self.registry.status()["modules"],
            "capabilities": sorted(self.self_model.capabilities),
        }
        self.state.history.append(snapshot)
        return snapshot

    def status(self):
        return {
            "version": "V2000",
            "cycle": self.state.cycle,
            "active_goal": self.state.active_goal,
            "modules": self.registry.status()["modules"],
            "goal_count": len(self.goals.goals),
            "evidence_count": len(self.research.evidence),
            "agent_messages": len(self.agents.messages),
            "capabilities": sorted(self.self_model.capabilities),
        }
