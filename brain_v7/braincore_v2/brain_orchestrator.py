"""Unified Brain V7 orchestrator.

Coordinates bounded cognition, capability planning, and a scalable management
hierarchy. External publication, money movement, credentials, legal
commitments and irreversible side effects remain permission-gated.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from time import time
from typing import Any, Iterable, Mapping

from .adaptive_priority_engine import PrioritySignal, rank_signals
from .cognitive_meta_controller import decide
from .cognitive_world_model import Hypothesis, Observation, update_many, rank_hypotheses
from .hierarchical_cognitive_architecture import Signal, cognitive_cycle
from .long_term_cognitive_memory import MemoryNode, MemoryObservation, Relation, consolidate, infer
from .cognitive_mesh import run_mesh
from .meta_learning_controller import StrategyObservation, recommend
from .cognitive_ecosystem import ecosystem_snapshot
from .capability_hub import CapabilityHub
from .employee_hierarchy import EmployeeHierarchy
from .notifications import NotificationCenter
from .workforce_evolution import WorkforceEvolutionEngine
from .leadership_evolution import LeadershipEvolutionEngine
from .advanced_talent import AdvancedTalentEngine
from .cyber_immune import CyberImmuneSystem
from .medical_unit import MedicalUnit
from .intelligence_center import IntelligenceCenter


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
    SAFE_INTERNAL_ACTIONS = {
        "observe", "remember", "reason", "simulate", "prioritize",
        "develop", "verify_local", "learn", "replan", "delegate",
    }

    BLOCKED_AUTONOMOUS_ACTIONS = {
        "transfer_money", "withdraw_money", "borrow_money", "trade_real_money",
        "open_bank_account", "sign_contract", "publish_irreversible_legal_statement",
        "delete_repository", "rotate_credentials", "read_secret",
    }

    def __init__(
        self,
        *,
        memory: Iterable[MemoryNode] = (),
        relations: Iterable[Relation] = (),
        strategy_history: Iterable[StrategyObservation] = (),
        initial_employees: int | None = None,
    ) -> None:
        self.state = BrainState(started_at=time())
        self.memory = {m.key: m for m in memory}
        self.relations = list(relations)
        self.strategy_history = list(strategy_history)
        self.capabilities = CapabilityHub()
        # Organizational layer: one Brain -> managers -> departments -> employees.
        self.organization = EmployeeHierarchy(initial_employees=initial_employees)
        self.notifications = NotificationCenter()
        self.workforce = WorkforceEvolutionEngine(self.organization, self.notifications)
        self.leadership = LeadershipEvolutionEngine(self.organization, self.notifications)
        self.talent = AdvancedTalentEngine(self.organization)
        self.immune = CyberImmuneSystem(self.organization)
        self.medical = MedicalUnit(self.immune)
        self.intelligence = IntelligenceCenter(self.notifications)

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

        self._observe(observation_list)

        hierarchy = cognitive_cycle(signal_list, causal_links=causal_links, plans=plans)

        mesh = run_mesh(
            objective,
            evidence=(
                sum(x.reliability for x in signal_list) / len(signal_list)
                if signal_list else 0.5
            ),
        )

        world = update_many(
            hypothesis_list,
            [
                Observation(
                    hypothesis_key=o.key,
                    outcome=o.outcome,
                    reliability=o.reliability,
                    source=o.source,
                )
                for o in observation_list
                if o.key
            ],
        )
        ranked_world = rank_hypotheses(world)

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

        meta = recommend(self.strategy_history)
        decision = decide(
            priority_signals,
            capability_gaps=[self._bottleneck()],
        ) if priority_signals else {"status": "NO_SIGNAL"}

        memory_inference = infer(self.memory, self.relations, iterations=3)

        focus = (
            decision.get("objective")
            or meta["decision"].get("selected", {}).get("mode")
            or self._bottleneck()
        )
        self.state.focus = str(focus)
        self.state.status = "READY_FOR_INTERNAL_DEVELOPMENT"

        capability_plan = self.capabilities.plan(objective)

        # The Brain delegates the current objective through the organization.
        delegated = self.organization.assign_task(objective)
        self.notifications.emit(
            "TASK_ASSIGNED",
            sender_id="BRAIN-001",
            recipient_id=delegated.assigned_to or delegated.manager_id or "BRAIN-001",
            message=f"Task {delegated.task_id} assigned for objective",
            priority="NORMAL",
            task_id=delegated.task_id,
            data={"objective": objective, "status": delegated.status},
        )
        evolution = self.workforce.evolve(objective)
        for employee_id in list(self.organization.employees)[:10]:
            self.talent.develop(employee_id)
            self.immune.scan_employee(self.organization.employees[employee_id])
        talent_snapshot = self.talent.organization_snapshot()
        immune_snapshot = self.immune.health()
        medical_snapshot = self.medical.snapshot()
        intelligence_snapshot = self.intelligence.snapshot()
        leadership = self.leadership.run()

        return {
            "cycle": self.state.cycle,
            "objective": objective,
            "hierarchical_reasoning": hierarchy,
            "cognitive_mesh": mesh,
            "world_model": {"hypotheses": [asdict(x) for x in ranked_world]},
            "adaptive_priority": priorities,
            "meta_learning": meta,
            "meta_decision": decision,
            "long_term_inference": memory_inference,
            "selected_internal_focus": self.state.focus,
            "capability_plan": capability_plan,
            "delegated_task": asdict(delegated),
            "organization": self.organization.snapshot(),
            "workforce_evolution": evolution,
            "notifications": self.notifications.snapshot(),
            "leadership": leadership,
            "talent_development": talent_snapshot,
            "cyber_immune": immune_snapshot,
            "medical_unit": medical_snapshot,
            "intelligence_center": intelligence_snapshot,
            "allowed_next_actions": sorted(self.SAFE_INTERNAL_ACTIONS),
            "blocked_autonomous_actions": sorted(self.BLOCKED_AUTONOMOUS_ACTIONS),
            "external_side_effects": False,
            "money_movement": False,
            "capability_hub": self.capabilities.snapshot(),
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
            "capability_hub": self.capabilities.snapshot(),
            "organization": self.organization.snapshot(),
            "workforce_evolution": {
                "continuous_evolution": True,
                "max_active_workers": self.workforce.max_active_workers,
                "max_new_per_cycle": self.workforce.max_new_per_cycle,
            },
            "notifications": self.notifications.snapshot(),
            "leadership": self.leadership.snapshot(),
            "talent_development": self.talent.organization_snapshot(),
            "cyber_immune": self.immune.snapshot(),
            "medical_unit": self.medical.snapshot(),
            "intelligence_center": self.intelligence.snapshot(),
        }


def build_brain(**kwargs: Any) -> UnifiedBrain:
    return UnifiedBrain(**kwargs)
