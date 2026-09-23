"""Unified Brain V7 orchestrator.

Coordinates the existing cognitive ecosystem into one bounded decision cycle:
observe -> remember -> reason -> compare -> simulate -> prioritize -> develop
-> verify -> learn -> repeat.

It can choose internal development work without asking the user each cycle.
External publication, money movement, credential access, legal commitments and
irreversible side effects remain explicitly gated by the existing governance
layer.

This is an orchestration engine, not a claim of superhuman intelligence.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from time import time
from typing import Any, Iterable, Mapping

from .adaptive_priority_engine import PrioritySignal, rank_signals
from .cognitive_meta_controller import decide
from .cognitive_world_model import (
    Hypothesis,
    Observation,
    update_many,
    rank_hypotheses,
)
from .hierarchical_cognitive_architecture import (
    Signal,
    cognitive_cycle,
)
from .long_term_cognitive_memory import (
    MemoryNode,
    MemoryObservation,
    Relation,
    consolidate,
    infer,
)
from .cognitive_mesh import run_mesh
from .meta_learning_controller import (
    StrategyObservation,
    recommend,
)
from .cognitive_ecosystem import ecosystem_snapshot


@dataclass
class BrainState:
    cycle: int = 0
    objective: str = ""
    focus: str = ""
    status: str = "IDLE"
    last_learning_reward: float = 0.0
    started_at: float = 0.0
    updated_at: float = 0.0


class UnifiedBrain:
    """Bounded autonomous internal coordinator."""

    SAFE_INTERNAL_ACTIONS = {
        "observe",
        "remember",
        "reason",
        "simulate",
        "prioritize",
        "develop",
        "verify_local",
        "learn",
        "replan",
    }

    BLOCKED_AUTONOMOUS_ACTIONS = {
        "transfer_money",
        "withdraw_money",
        "borrow_money",
        "trade_real_money",
        "open_bank_account",
        "sign_contract",
        "publish_irreversible_legal_statement",
        "delete_repository",
        "rotate_credentials",
        "read_secret",
    }

    def __init__(
        self,
        *,
        memory: Iterable[MemoryNode] = (),
        relations: Iterable[Relation] = (),
        strategy_history: Iterable[StrategyObservation] = (),
    ) -> None:
        self.state = BrainState(started_at=time())
        self.memory = {m.key: m for m in memory}
        self.relations = list(relations)
        self.strategy_history = list(strategy_history)

    def _observe(self, observations: Iterable[MemoryObservation]) -> None:
        self.memory = consolidate(self.memory.values(), observations)

    def cycle(
        self,
        objective: str,
        *,
        signals: Iterable[Signal] = (),
        observations: Iterable[MemoryObservation] = (),
        hypotheses: Iterable[Hypothesis] = (),
        causal_links: Iterable[Any] = (),
        plans: Mapping[str, Mapping[str, float]] | None = None,
    ) -> dict:
        self.state.cycle += 1
        self.state.objective = objective
        self.state.status = "REASONING"
        self.state.updated_at = time()

        signal_list = list(signals)
        observation_list = list(observations)
        hypothesis_list = list(hypotheses)

        # 1) Persistent memory
        self._observe(observation_list)

        # 2) Hierarchical reasoning
        hierarchy = cognitive_cycle(
            signal_list,
            causal_links=causal_links,
            plans=plans,
        )

        # 3) Parallel specialist reasoning
        mesh = run_mesh(
            objective,
            evidence=(
                sum(x.reliability for x in signal_list) / len(signal_list)
                if signal_list else 0.5
            ),
        )

        # 4) World-model update
        world = update_many(hypothesis_list, [
            Observation(
                hypothesis_key=o.key,
                outcome=o.outcome,
                reliability=o.reliability,
                source=o.source,
            )
            for o in observation_list
            if o.key
        ])
        ranked_world = rank_hypotheses(world)

        # 5) Adaptive priority
        priority_signals = []
        for item in hierarchy.get("alternatives", []):
            priority_signals.append(PrioritySignal(
                domain=item["plan"],
                opportunity_value=item["value"],
                speed=1.0 - item["risk"],
                outcome=item["confidence"],
                repeatability=item["reversibility"],
                evidence=item["confidence"],
                freshness=1.0,
                uncertainty=1.0 - item["confidence"],
                attempts=1,
                failures=0,
            ))
        priorities = rank_signals(priority_signals) if priority_signals else []

        # 6) Meta-learning chooses a reasoning mode, not a permission level.
        meta = recommend(self.strategy_history)

        # 7) Meta-controller integrates the adaptive signals.
        decision = decide(
            priority_signals,
            capability_gaps=[self._bottleneck()],
        ) if priority_signals else {"status": "NO_SIGNAL"}

        # 8) Recurrent memory inference.
        memory_inference = infer(self.memory, self.relations, iterations=3)

        # 9) Choose only bounded internal development.
        focus = (
            decision.get("objective")
            or meta["decision"].get("selected", {}).get("mode")
            or self._bottleneck()
        )
        self.state.focus = str(focus)
        self.state.status = "READY_FOR_INTERNAL_DEVELOPMENT"

        return {
            "cycle": self.state.cycle,
            "objective": objective,
            "hierarchical_reasoning": hierarchy,
            "cognitive_mesh": mesh,
            "world_model": {
                "hypotheses": [asdict(x) for x in ranked_world],
            },
            "adaptive_priority": priorities,
            "meta_learning": meta,
            "meta_decision": decision,
            "long_term_inference": memory_inference,
            "selected_internal_focus": self.state.focus,
            "allowed_next_actions": sorted(self.SAFE_INTERNAL_ACTIONS),
            "blocked_autonomous_actions": sorted(self.BLOCKED_AUTONOMOUS_ACTIONS),
            "external_side_effects": False,
            "money_movement": False,
            "requires_user_for_external_side_effects": True,
        }

    def _bottleneck(self) -> str:
        snapshot = ecosystem_snapshot()
        return snapshot["layers"][0]["name"] if snapshot.get("layers") else "COGNITIVE_REASONING"

    def snapshot(self) -> dict:
        return {
            "state": asdict(self.state),
            "memory_nodes": len(self.memory),
            "relations": len(self.relations),
            "strategy_history": len(self.strategy_history),
            "autonomous_internal_cycles": True,
            "external_side_effects": False,
            "permission_escalation": False,
        }


def build_brain(**kwargs: Any) -> UnifiedBrain:
    return UnifiedBrain(**kwargs)
