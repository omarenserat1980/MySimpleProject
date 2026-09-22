from dataclasses import dataclass, field

@dataclass
class WorldState:
    position: int = 0
    goal: int = 4
    energy: float = 1.0
    step: int = 0
    hidden_risk: dict[int, float] = field(default_factory=dict)
    last_action: str | None = None

class MiniWorld:
    ACTIONS = ("LEFT", "RIGHT", "WAIT")
    def __init__(self, goal: int = 4, start: int = 0):
        self.state = WorldState(position=start, goal=goal)
        self.reset_count = 0

    def observe(self) -> dict:
        s = self.state
        return {"position": s.position, "goal": s.goal, "energy": s.energy,
                "step": s.step, "last_action": s.last_action,
                "local_risk": s.hidden_risk.get(s.position, 0.0)}

    def step(self, action: str) -> dict:
        action = action.upper()
        if action not in self.ACTIONS:
            return {"ok": False, "error": "INVALID_ACTION"}
        s = self.state
        old = s.position
        if action == "RIGHT": s.position = min(s.goal, s.position + 1)
        elif action == "LEFT": s.position = max(0, s.position - 1)
        s.step += 1
        s.energy = max(0.0, s.energy - (0.04 if action != "WAIT" else 0.01))
        s.last_action = action
        risk = s.hidden_risk.get(s.position, 0.0)
        reached = s.position == s.goal
        reward = 10.0 if reached else (-2.0 * risk - 0.1)
        return {"ok": True, "from": old, "to": s.position, "action": action,
                "reward": reward, "risk": risk, "reached": reached,
                "energy": s.energy, "step": s.step}

    def reset(self):
        goal = self.state.goal
        self.state = WorldState(position=0, goal=goal)
        self.reset_count += 1
