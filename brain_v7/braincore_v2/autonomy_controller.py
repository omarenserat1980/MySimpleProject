"""Permission-aware control plane for long-running autonomy."""
from __future__ import annotations
from dataclasses import asdict,dataclass
from typing import Any
from .capability_registry import capability_summary
from .autonomous_development_supervisor import plan_next as plan_development
from .revenue_engine import rank_with_financials
from .governance import evaluate_action,append_audit,policy_snapshot
@dataclass(frozen=True)
class ControlPlan:
    objective:str
    development:dict[str,Any]
    revenue_candidates:list[dict[str,Any]]
    safe_actions:list[str]
    blocked_actions:list[str]
def build_plan(objective:str="increase verified earning capability")->dict[str,Any]:
    dev=plan_development(); ranked=rank_with_financials()
    candidates=ranked[:5]
    actions=["inspect","pytest_collect","workspace_tree","git_status","revenue_rank","self_develop"]
    safe=[]; blocked=[]
    for action in actions:
        d=evaluate_action(action)
        (safe if d.allowed else blocked).append(action)
    plan=ControlPlan(str(objective),dev,candidates,safe,blocked)
    result={"plan":asdict(plan),"capabilities":capability_summary(),"policy":policy_snapshot()}
    append_audit("control_plan",result)
    return result
