"""Self-directed loop joining goals, planning, execution, observation and learning."""
from .autonomous_goals import AutonomousGoalEngine

class AutonomousLoop:
    def __init__(self, core):
        self.core = core
        self.goals = AutonomousGoalEngine()

    def step(self, state: dict):
        candidates = self.goals.generate(state)
        goal = self.goals.select()
        if goal is None:
            return {"status": "IDLE", "reason": "no_pending_goal"}

        result = self.core.cycle({
            "action": state.get("action", "inspect"),
            "goal_id": goal.id,
            "goal": goal.description,
            "steps": goal.steps,
            "state": state,
        })

        if result.get("status") == "EXECUTED":
            self.goals.complete(goal.id)

        return {
            "status": result.get("status"),
            "goal": goal.description,
            "goal_id": goal.id,
            "result": result,
            "goal_engine": self.goals.status(),
        }
