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
from .digital_state import DigitalState
from .revenue_task_factory import RevenueTaskFactory
from .revenue_challenge import RevenueChallenge
from .external_work_gateway import ExternalWorkGateway
from .completion_orchestrator import evaluate as evaluate_completion
from .adaptive_reasoning_engine import AdaptiveReasoningEngine
from .adaptive_learning_loop import AdaptiveLearningLoop
from .reasoning_quality_controller import ReasoningQualityController
from .operational_control_plane import OperationalControlPlane
from .cognitive_workforce import CognitiveWorkforce
from .code_workspace_tool import CodeWorkspaceTool, CodeChange
from .code_tool_engineering_team import CodeToolEngineeringTeam


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
        self.digital_state = DigitalState()
        self.revenue_factory = RevenueTaskFactory()
        self.revenue_challenge = RevenueChallenge(self.organization)
        self.external_work = ExternalWorkGateway(self.organization)
        self.reasoning_engine = AdaptiveReasoningEngine()
        self.adaptive_learning = AdaptiveLearningLoop()
        self.quality_controller = ReasoningQualityController()
        self.control_plane = OperationalControlPlane()
        self.cognitive_workforce = CognitiveWorkforce()
        # Controlled self-development tool: source changes stay inside the configured workspace.
        self.code_workspace = CodeWorkspaceTool()
        self.code_tool_team = CodeToolEngineeringTeam(self.organization, self.code_workspace)

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
        outcome: str = "unknown",
        reward: float = 0.0,
        outcome_evidence: str = "",
    ) -> dict:
        self.state.cycle += 1
        self.state.objective = objective
        self.state.status = "REASONING"
        self.state.updated_at = time()
        self.control_plane.heartbeat("BRAIN-001", cycle=self.state.cycle, detail="reasoning_cycle_started")

        signal_list = list(signals)
        observation_list = list(observations)
        hypothesis_list = list(hypotheses)

        self._observe(observation_list)

        # Dedicated understanding/reasoning/flexibility layer. It competes
        # multiple interpretations before the older planners choose actions.
        reasoning = self.reasoning_engine.reason(
            objective,
            context={
                "cycle": self.state.cycle,
                "memory_nodes": len(self.memory),
                "signals": len(signal_list),
            },
            evidence=[
                f"signal:{s.name}" for s in signal_list if getattr(s, "name", None)
            ],
            observations=[
                {
                    "statement": getattr(o, "outcome", ""),
                    "polarity": "support" if getattr(o, "reliability", 0.0) >= 0.5 else "against",
                }
                for o in observation_list
            ],
        )

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

        specialist_proposals = []
        for index, hypothesis in enumerate(reasoning.hypotheses[:6], start=1):
            specialist_proposals.append({
                "employee_id": f"COG-{index:03d}",
                "role": hypothesis.label,
                "proposal": hypothesis.interpretation.text,
                "confidence": hypothesis.confidence,
                "evidence": len(hypothesis.evidence_for),
                "reversible": hypothesis.reversibility,
            })
        cognitive_workforce = self.cognitive_workforce.review(objective, specialist_proposals)

        quality = self.quality_controller.evaluate(
            understanding_confidence=reasoning.interpretation.confidence,
            evidence_count=len(reasoning.interpretation.entities) + len(observation_list),
            contradiction_count=len(reasoning.contradictions),
            alternative_count=len(reasoning.hypotheses),
            reversibility=max(
                (h.reversibility for h in reasoning.hypotheses),
                default=0.0,
            ),
        )

        candidate_strategies = [
            reasoning.selected_strategy,
            *[h.label for h in reasoning.hypotheses],
            decision.get("objective", ""),
            meta["decision"].get("selected", {}).get("mode", ""),
            self._bottleneck(),
        ]
        learning_recommendation = self.adaptive_learning.recommend(candidate_strategies)
        learned_focus = learning_recommendation.get("selected")
        focus = (
            learned_focus
            if learned_focus and learning_recommendation.get("confidence", 0.0) >= 0.55
            else reasoning.selected_strategy
            if reasoning.confidence >= 0.55
            else decision.get("objective")
            or meta["decision"].get("selected", {}).get("mode")
            or self._bottleneck()
        )
        self.state.focus = str(focus)
        self.state.status = "READY_FOR_INTERNAL_DEVELOPMENT"

        capability_plan = self.capabilities.plan(objective)
        code_tool_plan = self.code_tool_team.plan_cycle()
        code_workspace = self.code_workspace.snapshot()

        # Diversified revenue experiments: different employees receive different lawful paths.
        revenue_tasks = self.revenue_factory.generate(count=8)
        revenue_assignments = []
        for item in revenue_tasks:
            task = self.organization.assign_task(item["objective"])
            revenue_assignments.append({"revenue_task": item, "employee_task": asdict(task)})

        external_work_snapshot = self.external_work.snapshot()
        completion_report = evaluate_completion({
            "cognition_memory": True,
            "organization": self.organization.snapshot(),
            "revenue_challenge": self.revenue_challenge.snapshot(),
            "external_work": external_work_snapshot,
            "cinematic_factory": {
                "shot_generation": True,
                "video_assembly": True,
                "authorized_publication": True,
                "analytics_feedback": True,
                "next_cycle_learning": True,
            },
            "safety_gates": True,
            "deployment": {"configured": False},
            "code_tool_engineering": self.code_tool_team.snapshot(),
        })

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
        state_snapshot = self.digital_state.dashboard()
        leadership = self.leadership.run()
        control_plane = self.control_plane.snapshot()
        # Record only observable internal outcome signals. A cycle without an
        # explicit completion/failure result remains UNKNOWN; no success is invented.
        normalized_outcome = str(outcome).lower().strip()
        if normalized_outcome not in {"success", "failure", "unknown"}:
            normalized_outcome = "unknown"
        evidence = outcome_evidence
        if normalized_outcome == "unknown" and not evidence:
            evidence = "cycle_completed_without_external_success_evidence"
        self.adaptive_learning.record_outcome(
            cycle=self.state.cycle,
            objective=objective,
            strategy=str(focus),
            outcome=normalized_outcome,
            reward=float(reward),
            evidence=evidence,
        )
        self.control_plane.heartbeat("BRAIN-001", cycle=self.state.cycle, detail="reasoning_cycle_complete")

        return {
            "cycle": self.state.cycle,
            "objective": objective,
            "adaptive_reasoning": asdict(reasoning),
            "reasoning_quality": asdict(quality),
            "cognitive_workforce": cognitive_workforce,
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
            "revenue_tasks": revenue_assignments,
            "revenue_challenge": self.revenue_challenge.progress(),
            "external_work": external_work_snapshot,
            "external_work_metrics": self.external_work.metrics(),
            "completion_report": completion_report,
            "organization": self.organization.snapshot(),
            "workforce_evolution": evolution,
            "notifications": self.notifications.snapshot(),
            "leadership": leadership,
            "talent_development": talent_snapshot,
            "cyber_immune": immune_snapshot,
            "medical_unit": medical_snapshot,
            "intelligence_center": intelligence_snapshot,
            "digital_state": state_snapshot,
            "allowed_next_actions": sorted(self.SAFE_INTERNAL_ACTIONS),
            "blocked_autonomous_actions": sorted(self.BLOCKED_AUTONOMOUS_ACTIONS),
            "external_side_effects": False,
            "money_movement": False,
            "capability_hub": self.capabilities.snapshot(),
            "code_workspace": code_workspace,
            "code_tool_engineering": self.code_tool_team.snapshot(),
            "code_tool_plan": code_tool_plan,
            "reasoning_engine": self.reasoning_engine.snapshot(),
            "adaptive_learning": self.adaptive_learning.snapshot(),
            "learning_recommendation": learning_recommendation,
            "outcome": {"status": normalized_outcome, "reward": float(reward), "evidence": evidence},
            "operational_control_plane": control_plane,
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
            "digital_state": self.digital_state.snapshot(),
            "revenue_factory": self.revenue_factory.snapshot(),
            "revenue_challenge": self.revenue_challenge.snapshot(),
            "external_work": self.external_work.snapshot(),
            "reasoning_engine": self.reasoning_engine.snapshot(),
            "adaptive_learning": self.adaptive_learning.snapshot(),
            "reasoning_quality_controller": self.quality_controller.snapshot(),
            "operational_control_plane": self.control_plane.snapshot(),
            "cognitive_workforce": self.cognitive_workforce.snapshot(),
            "code_workspace": self.code_workspace.snapshot(),
            "code_tool_engineering": self.code_tool_team.snapshot(),
        }


def build_brain(**kwargs: Any) -> UnifiedBrain:
    return UnifiedBrain(**kwargs)
