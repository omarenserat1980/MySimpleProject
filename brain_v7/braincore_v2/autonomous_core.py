"""Bounded autonomous core.

Provides a self-directed cycle: inspect -> choose goal -> decompose -> act through
registered safe callbacks -> observe -> learn -> continue. It never executes
arbitrary host commands by itself; external tools must be explicitly registered.
"""
from dataclasses import dataclass, field
from typing import Any, Callable
from .v2000_integrated import V2000Brain

@dataclass
class AutonomousState:
    running: bool = False
    cycle: int = 0
    completed: int = 0
    failed: int = 0
    observations: list[dict] = field(default_factory=list)

class AutonomousCore:
    def __init__(self):
        self.brain = V2000Brain()
        self.state = AutonomousState()
        self.actions: dict[str, Callable[[dict], Any]] = {}

    def register_action(self, name: str, handler: Callable[[dict], Any]):
        self.actions[name] = handler

    def start(self, objective: str):
        if not self.brain.state.active_goal:
            self.brain.create_goal("autonomous.root", objective, priority=1.0)
        self.state.running = True
        return self.status()

    def stop(self):
        self.state.running = False
        return self.status()

    def cycle(self, observation: dict | None = None):
        if not self.state.running:
            return {"status": "STOPPED"}
        self.state.cycle += 1
        observation = observation or {}
        self.state.observations.append(observation)

        goal = self.brain.goals.goals.get(self.brain.state.active_goal)
        if not goal:
            self.state.running = False
            return {"status": "NO_GOAL"}

        # Choose a registered action. Unknown actions remain proposals, not execution.
        action_name = observation.get("action", "inspect")
        handler = self.actions.get(action_name)
        if handler is None:
            result = {"status": "PROPOSED", "action": action_name, "reason": "ACTION_NOT_REGISTERED"}
        else:
            try:
                result = {"status": "EXECUTED", "action": action_name, "result": handler(observation)}
                self.state.completed += 1
            except Exception as exc:
                self.state.failed += 1
                result = {"status": "FAILED", "action": action_name, "error": str(exc)}

        self.brain.cycle(result)
        return result

    def status(self):
        return {
            "version": "V2000-AUTONOMOUS",
            "running": self.state.running,
            "cycle": self.state.cycle,
            "completed": self.state.completed,
            "failed": self.state.failed,
            "registered_actions": sorted(self.actions),
            "brain": self.brain.status(),
        }
