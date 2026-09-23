"""Permission-aware control plane for long-running autonomy.

The controller joins three loops: capability growth, economic opportunity
selection, and governance. It plans; it does not grant financial authority.
"""
from __future__ import annotations
from dataclasses import asdict,dataclass
from typing import Any
from .capability_registry import capability_summary
from .autonomous_development_supervisor import plan_next as plan_development
from .revenue_engine import rank_with_financials
from .economic_controller import evaluate
from .governance import evaluate_action,append_audit,policy_snapshot
from .solution_forge import forge

@dataclass(frozen=True)
class ControlPlan:
    objective:str
    development:dict[str,Any]
    revenue_candidates:list[dict[str,Any]]
    economic_frontier:list[dict[str,Any]]
    safe_actions:list[str]
    blocked_actions:list[str]

def build_plan(objective:str="increase verified earning capability")->dict[str,Any]:
    dev=plan_development()
    ranked=rank_with_financials()
    candidates=ranked[:5]
    economic_frontier=[]
    for row in candidates:
        # Reconstruct only the public opportunity fields; no payment is assumed.
        from .revenue_engine import Opportunity
        opportunity=Opportunity(
            row["name"],row["service"],float(row["expected_jod"]),
            float(row["effort_hours"]),float(row["demand"]),
            float(row["proofability"]),float(row["platform_friction"])
        )
        economic_frontier.append(evaluate(opportunity).__dict__)

    actions=["inspect","pytest_collect","workspace_tree","git_status","revenue_rank","solution_forge","self_develop"]
    safe=[]; blocked=[]
    for action in actions:
        d=evaluate_action(action)
        (safe if d.allowed else blocked).append(action)

    plan=ControlPlan(str(objective),dev,candidates,economic_frontier,safe,blocked)
    result={"plan":asdict(plan),"creative_frontier":forge(objective),"capabilities":capability_summary(),"policy":policy_snapshot()}
    append_audit("control_plan",result)
    return result
