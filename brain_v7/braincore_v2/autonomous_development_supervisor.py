"""Bounded supervisor for autonomous development.

It chooses the next engineering objective from the capability gap, records
attempts, and enforces iteration/resource limits. It cannot grant permissions,
move money, deploy itself, or rewrite protected code by itself.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import json, os, time
from pathlib import Path
from typing import Any
from .self_development_engine import next_development
from .capability_registry import capability_summary

STATE_PATH = Path(os.getenv("BRAIN_DEV_SUPERVISOR_STATE", "development_supervisor.json"))
MAX_ITERATIONS = 8
PROTECTED_DOMAINS = frozenset({"banking","crypto","stocks","law_compliance"})

@dataclass(frozen=True)
class DevelopmentTask:
    task_id: str
    domain: str
    objective: str
    evidence: str

def _load() -> dict[str, Any]:
    try:
        data=json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def _save(data: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def plan_next() -> dict[str, Any]:
    choice=next_development()
    if choice["status"] != "READY":
        return {"status":"NO_WORK","reason":"NO_PENDING_DOMAIN"}
    d=choice["next"]
    task=DevelopmentTask(
        task_id=f"dev-{int(time.time())}",
        domain=d["name"],
        objective=f"Build and test measurable capability for {d['name']}",
        evidence=d["evidence_required"],
    )
    return {"status":"PLANNED","task":asdict(task),"capability_summary":capability_summary()["counts"]}

def task_is_safe(task: dict[str, Any]) -> bool:
    """Only permit bounded capability-building tasks; sensitive domains require evidence."""
    domain=str(task.get("domain",""))
    return domain not in PROTECTED_DOMAINS or bool(str(task.get("evidence","")).strip())

def record_attempt(task_id: str, passed: bool, evidence: str="") -> dict[str, Any]:
    data=_load()
    history=data.setdefault("attempts", [])
    if len(history) >= MAX_ITERATIONS:
        return {"status":"BLOCKED","reason":"ITERATION_LIMIT"}
    item={"task_id":str(task_id),"passed":bool(passed),"evidence":str(evidence),"timestamp":time.time()}
    history.append(item)
    data["last_task"]=item
    _save(data)
    return item

def status() -> dict[str, Any]:
    data=_load()
    return {"attempts":data.get("attempts",[])[-MAX_ITERATIONS:], "next":plan_next()}
