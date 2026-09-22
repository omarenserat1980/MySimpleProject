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

    def _execute(self, action: str, state: dict):
        if self.action_executor is None:
            return {"status": "PROPOSED", "action": action}
        try:
            return self.action_executor(action, state)
        except Exception as exc:
            return {"status": "FAILED", "error": str(exc), "action": action}

    def step(self, state: dict):
        self.cycle += 1
        self.goals.generate(state)
        goal = self.goals.select()
        if goal is None:
            return {"status": "IDLE", "cycle": self.cycle}

        actions = state.get("actions") or goal.steps
        if not actions:
            return {"status": "IDLE", "cycle": self.cycle, "reason": "NO_ACTIONS"}

        plan = self.planner.propose(goal.description, actions, state.get("horizon", 5))
        plan = self.planner.simulate(plan, state)
        action = self.learning.best_action(actions) or actions[0]
        outcome = self._execute(action, state)

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

    def run_loop(self, state: dict):
        """Run a bounded multi-step loop, stopping safely on the first failure."""
        actions = list(state.get("actions") or [])
        horizon = max(1, min(int(state.get("horizon", len(actions) or 1)), 20))
        actions = actions[:horizon]
        if not actions:
            return {"status": "IDLE", "steps": [], "reason": "NO_ACTIONS"}

        self.cycle += 1
        self.goals.generate(state)
        goal = self.goals.select()
        goal_id = goal.id if goal else f"loop-{self.cycle}"
        goal_description = goal.description if goal else state.get("objective", "autonomous loop")

        plan = self.planner.propose(goal_description, actions, horizon)
        plan = self.planner.simulate(plan, state)
        results = []

        for index, action in enumerate(actions, 1):
            step_state = dict(state)
            step_state["step"] = index
            step_state["previous_results"] = results[-3:]
            outcome = self._execute(action, step_state)
            expected = state.get("action_expectations", {}).get(action, state.get("expected"))
            reward = 1.0 if outcome.get("status") == "EXECUTED" else 0.0

            experience = self.learning.learn(
                goal_id=goal_id,
                action=action,
                expected=expected,
                actual=outcome,
                cycle=self.cycle,
            )
            self.world.observe(step_state, action, outcome, outcome, reward)

            results.append({
                "step": index,
                "action": action,
                "status": outcome.get("status"),
                "outcome": outcome,
                "learning": {
                    "error": experience.error,
                    "reward": experience.reward,
                    "lesson": experience.lesson,
                },
            })

            if outcome.get("status") != "EXECUTED":
                return {
                    "status": "STOPPED",
                    "reason": "ACTION_FAILED_OR_PROPOSED",
                    "cycle": self.cycle,
                    "goal": goal_description,
                    "goal_id": goal_id,
                    "completed_steps": index - 1,
                    "results": results,
                    "world": self.world.status(),
                }

        if goal:
            self.goals.complete(goal.id)

        return {
            "status": "COMPLETED",
            "cycle": self.cycle,
            "goal": goal_description,
            "goal_id": goal_id,
            "completed_steps": len(results),
            "plan": [{"action": s.action, "expected": s.expected, "risk": s.risk} for s in plan.steps],
            "plan_score": plan.score,
            "results": results,
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
