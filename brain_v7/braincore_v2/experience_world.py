"""Persistent experience memory and lightweight learned world model."""
from dataclasses import dataclass
from typing import Any

@dataclass
class Transition:
    state_key: str
    action: str
    next_state_key: str
    outcome: Any
    reward: float
    count: int = 1

class ExperienceWorld:
    def __init__(self):
        self.transitions: dict[tuple[str,str], Transition] = {}
        self.state_counts: dict[str, int] = {}

    @staticmethod
    def key(state: dict | str) -> str:
        if isinstance(state, str):
            return state
        return repr(sorted((str(k), repr(v)) for k, v in state.items()))

    def observe(self, state: dict | str, action: str, next_state: dict | str,
                outcome: Any, reward: float):
        sk, nk = self.key(state), self.key(next_state)
        self.state_counts[nk] = self.state_counts.get(nk, 0) + 1
        key = (sk, action)
        old = self.transitions.get(key)
        if old:
            old.count += 1
            old.next_state_key = nk
            old.outcome = outcome
            old.reward = old.reward + (reward - old.reward) / old.count
        else:
            self.transitions[key] = Transition(sk, action, nk, outcome, reward)

    def predict(self, state: dict | str, action: str) -> dict | None:
        t = self.transitions.get((self.key(state), action))
        if not t:
            return None
        return {"next_state": t.next_state_key, "outcome": t.outcome,
                "reward": t.reward, "confidence": min(1.0, t.count / 10)}

    def status(self):
        return {"transitions": len(self.transitions), "known_states": len(self.state_counts)}
