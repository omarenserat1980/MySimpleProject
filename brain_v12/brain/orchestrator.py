from __future__ import annotations

from typing import Any

from .core import BrainCore
from .builder import SoftwareBuilder
from .execution_coordinator import BrainExecutionCoordinator


class CognitiveOrchestrator:
    """Single owner for the V12 perceive -> decide -> plan -> observe -> learn cycle."""

    def __init__(self, store, brain: BrainCore, builder: SoftwareBuilder, execution_coordinator: BrainExecutionCoordinator | None = None):
        self.store = store
        self.brain = brain
        self.builder = builder
        self.execution_coordinator = execution_coordinator or BrainExecutionCoordinator()

    def run(self, project: str = "brain_v12") -> dict[str, Any]:
        decision = self.brain.think()
        if decision.get("status") != "DECIDING":
            return {"status": decision.get("status", "IDLE"), "decision": decision}

        objective = decision["current_goal"]
        plan = self.builder.plan(project, objective)
        self.store.event("ORCHESTRATOR_PLAN", {"objective": objective, "plan": plan})

        state = self.brain.snapshot()
        state.update({
            "status": "PLANNED",
            "objective": objective,
            "decision": decision.get("selected"),
            "plan": plan,
        })
        self.store.set_state(state)
        execution = self.execution_coordinator.create(objective)
        self.store.event("ORCHESTRATOR_EXECUTION_CREATED", {
            "objective": objective,
            "control_task_id": execution["control"]["id"],
            "path_run_id": execution["path"]["run_id"],
        })
        state = self.store.state()
        state.update({"execution": execution})
        self.store.set_state(state)
        return {"status": "PLANNED", "decision": decision, "plan": plan, "execution": execution}

    def execute(self, control_task_id: str, executor, verifier, repair=None) -> dict[str, Any]:
        """Delegate execution to the single execution owner; never execute locally."""
        return self.execution_coordinator.execute(control_task_id, executor, verifier, repair=repair)

    def observe_and_learn(self, actual: str, lesson: str | None = None) -> dict[str, Any]:
        observed = self.brain.observe(actual)
        if lesson:
            self.brain.learn(lesson)
        return {
            "status": observed.get("status"),
            "observation": observed,
            "lesson": lesson,
        }
