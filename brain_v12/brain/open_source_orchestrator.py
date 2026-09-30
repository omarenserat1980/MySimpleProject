"""Operational capability selection for the optional open-source Brain stack.

Availability is authoritative. Learned evidence may reorder compatible backends,
but it can never activate an unavailable backend.
"""
from __future__ import annotations
from .capability_router import candidates, route
from .learning_router import load_observations, rank

def available_ids(status: dict) -> set[str]:
    return {x["id"] for x in status.get("services", []) if x.get("health",{}).get("available")}

def select_backend(task: str, status: dict, observation_path: str = "brain6_artifacts/backend_observations.jsonl") -> dict:
    available = available_ids(status)
    pool = [x for x in candidates(task) if x["id"] in available]
    if not pool:
        return route(task, available)
    ranked = rank(pool, task, load_observations(observation_path))
    return {
        "task": task,
        "candidates": ranked,
        "selected": ranked[0],
        "reason": "best compatible available backend using bounded execution evidence",
    }

def plan(tasks: list[str], status: dict, observation_path: str = "brain6_artifacts/backend_observations.jsonl") -> list[dict]:
    return [select_backend(task, status, observation_path) for task in tasks]
