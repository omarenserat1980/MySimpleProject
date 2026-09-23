"""Unified Brain V7 orchestrator.

Coordinates bounded cognition, capability planning, and a scalable management
hierarchy. External publication, money movement, credentials, legal
commitments and irreversible side effects remain permission-gated.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import json
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
from .continuous_self_improvement import ContinuousSelfImprovement
from .reasoning_quality_controller import ReasoningQualityController
from .operational_control_plane import OperationalControlPlane
from .cognitive_workforce import CognitiveWorkforce
from .code_workspace_tool import CodeWorkspaceTool, CodeChange
from .code_tool_engineering_team import CodeToolEngineeringTeam
from .code_tool_api import CodeTool
from .remote_ai_gateway import RemoteAIGateway


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
        self.self_improvement = ContinuousSelfImprovement()
        self.quality_controller = ReasoningQualityController()
        self.control_plane = OperationalControlPlane()
        self.cognitive_workforce = CognitiveWorkforce()
        # Controlled self-development tool: source changes stay inside the configured workspace.
        self.code_workspace = CodeWorkspaceTool(\n            allowed_prefixes=("brain_v7/",),\n        )
        self.code_tool_team = CodeToolEngineeringTeam(self.organization, self.code_workspace)