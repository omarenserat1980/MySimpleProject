"""Bounded, fail-closed execution protocol for design plans.

The default path is plan-only. One call can dispatch at most one step, and only
when the caller explicitly authorizes it and supplies an executor. This module
never grants permissions to external tools and never upgrades evidence to VERIFIED.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

ALLOWED_STEP_STATUSES = {"SIMULATED", "TESTED", "BLOCKED", "FAILED"}
TERMINAL_STATUSES = {"BLOCKED", "FAILED"}


def initialize_execution(plan: dict) -> dict:
    """Create an execution ledger from a PLANNED design plan without running it."""
    if not isinstance(plan, dict) or plan.get("status") != "PLANNED":
        raise ValueError("A plan with status PLANNED is required")
    task = plan.get("task")
    if not isinstance(task, str) or not task.strip():
        raise ValueError("Plan task is required")
    domains = plan.get("domains")
    if not isinstance(domains, list) or not domains:
        raise ValueError("Plan domains are required")
    steps = [
        {"step_id": f"step-{index:02d}", "domain": domain, "status": "PLANNED",
         "evidence": None, "started": False}
        for index, domain in enumerate(domains, start=1)
    ]
    return {
        "status": "PLANNED",
        "task": task,
        "steps": steps,
        "next_step_index": 0,
        "execution_started": False,
        "stopped": False,
        "events": [{"event": "PLAN_INITIALIZED", "status": "PLANNED"}],
        "policy": {
            "default_mode": "plan_only",
            "max_steps_per_call": 1,
            "side_effects_default": "DENY",
            "verified_status_may_be_emitted": False,
        },
    }


def execute_next_step(
    state: dict,
    executor: Callable[[dict], dict] | None = None,
    *,
    authorize: bool = False,
    dry_run: bool = True,
) -> dict:
    """Advance at most one step. Dry-run is the default and never calls executor."""
    if not isinstance(state, dict) or not isinstance(state.get("steps"), list):
        raise ValueError("A valid execution state is required")
    result = deepcopy(state)
    if result.get("stopped"):
        result["events"].append({"event": "EXECUTION_REFUSED", "reason": "PLAN_STOPPED"})
        return result
    index = result.get("next_step_index", 0)
    if not isinstance(index, int) or index < 0 or index >= len(result["steps"]):
        result["events"].append({"event": "NO_PENDING_STEP"})
        return result

    step = result["steps"][index]
    if dry_run:
        step["status"] = "PLANNED"
        step["evidence"] = {"kind": "PLAN_ONLY", "execution_performed": False}
        result["events"].append({
            "event": "STEP_PLANNED", "step_id": step["step_id"], "status": "PLANNED"
        })
        return result

    if not authorize:
        step["status"] = "BLOCKED"
        step["evidence"] = {"kind": "POLICY", "reason": "EXPLICIT_AUTHORIZATION_REQUIRED"}
        result["stopped"] = True
        result["status"] = "BLOCKED"
        result["events"].append({
            "event": "STEP_BLOCKED", "step_id": step["step_id"],
            "reason": "EXPLICIT_AUTHORIZATION_REQUIRED"
        })
        return result

    if not callable(executor):
        step["status"] = "BLOCKED"
        step["evidence"] = {"kind": "POLICY", "reason": "BLOCKED_NO_EXECUTOR"}
        result["stopped"] = True
        result["status"] = "BLOCKED"
        result["events"].append({
            "event": "STEP_BLOCKED", "step_id": step["step_id"],
            "reason": "BLOCKED_NO_EXECUTOR"
        })
        return result

    result["execution_started"] = True
    step["started"] = True
    try:
        executor_result = executor({"step_id": step["step_id"], "domain": step["domain"]})
        if not isinstance(executor_result, dict):
            raise TypeError("Executor must return a dict")
        reported_status = executor_result.get("status")
        if reported_status not in ALLOWED_STEP_STATUSES:
            raise ValueError("Executor status must be SIMULATED, TESTED, BLOCKED, or FAILED")
        evidence = executor_result.get("evidence")
        if not isinstance(evidence, dict):
            raise ValueError("Executor must return an evidence dictionary")
        step["status"] = reported_status
        step["evidence"] = evidence
        result["events"].append({
            "event": "STEP_RESULT", "step_id": step["step_id"], "status": reported_status
        })
        result["next_step_index"] = index + 1
        if reported_status in TERMINAL_STATUSES:
            result["stopped"] = True
            result["status"] = reported_status
        elif result["next_step_index"] >= len(result["steps"]):
            result["status"] = "TESTED" if reported_status == "TESTED" else "SIMULATED"
        else:
            result["status"] = "PLANNED"
    except Exception as exc:
        step["status"] = "FAILED"
        step["evidence"] = {"kind": "EXECUTOR_ERROR", "error": type(exc).__name__}
        result["stopped"] = True
        result["status"] = "FAILED"
        result["events"].append({
            "event": "STEP_FAILED", "step_id": step["step_id"],
            "error": type(exc).__name__
        })
    return result
