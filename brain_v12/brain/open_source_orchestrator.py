"""Operational capability selection for the optional open-source stack."""
from __future__ import annotations
from .capability_router import route

def available_ids(status: dict) -> set[str]:
    return {x["id"] for x in status.get("services", []) if x.get("health",{}).get("available")}

def select_backend(task: str, status: dict) -> dict:
    return route(task, available_ids(status))

def plan(tasks: list[str], status: dict) -> list[dict]:
    return [select_backend(task,status) for task in tasks]
