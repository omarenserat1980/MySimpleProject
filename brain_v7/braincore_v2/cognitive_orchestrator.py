"""Integrated bounded cognitive orchestrator."""
from .autonomous_goals import AutonomousGoalEngine
from .long_horizon_planner import LongHorizonPlanner
from .experience_world import ExperienceWorld
from .adaptive_learning import AdaptiveLearning
from .self_improvement import SelfImprovementEngine

class CognitiveOrchestrator:
    def __init__(self, action_executor=None):
        self.goals = AutonomousGoalEngine()
        self.planner = LongHorizonPlanner()
        self.world = ExperienceWorld()
        self.learning = AdaptiveLearning()
        self.improvement = SelfImprovementEngine()
        self.action_executor = action_executor
        self.cycle = 0

    def step(self, state: dict):
        self.cycle += 1
        candidates = self.goals.generate(state)
        goal = self.goals.select()
        if goal is None:
            return {"status": "IDLE", "cycle": self.cycle}

        actions = state.get("actions") or goal.steps
        plan = self.planner.propose(goal.description, actions, state.get("horizon", 5))
        plan = self.planner.simulate(plan, state)
        action = self.learning.best_action(actions) or actions[0]

        if self.action_executor is None:
            outcome = {"status": "PROPOSED", "action": action}
        else:
            try:
                outcome = self.action_executor(action, state)
            except Exception as exc:
                outcome = {"status": "FAILED", "error": str(exc), "action": action}

        reward = 1.0 if outcome.get("status") == "EXECUTED" else 0.0
        experience = self.learning.learn(
            goal_id=goal.id, action=action,
            expected=state.get("expected"), actual=outcome,
            cycle=self.cycle,
        )
        self.world.observe(state, action, outcome, outcome, reward)
        if outcome.get("status") == "EXECUTED":
            self.goals.complete(goal.id)

        return {
            "status": outcome.get("status"),
            "cycle": self.cycle,
            "goal": goal.description,
            "goal_id": goal.id,
            "plan": [{"action": s.action, "expected": s.expected, "risk": s.risk} for s in plan.steps],
            "plan_score": plan.score,
            "action": action,
            "outcome": outcome,
            "learning": {"error": experience.error, "reward": experience.reward},
            "world": self.world.status(),
        }

    def propose_improvement(self, proposal_id: str, description: str):
        return self.improvement.propose(proposal_id, description)

    def status(self):
        return {
            "cycle": self.cycle,
            "goals": self.goals.status(),
            "planner": self.planner.status(),
            "world": self.world.status(),
            "learning": self.learning.status(),
            "improvement": self.improvement.status(),
        }
