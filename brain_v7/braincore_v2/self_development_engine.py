"""Self-development engine for the Electronic Brain.

This module turns the broad "develop yourself" goal into measurable,
bounded engineering work. It does not grant new permissions, move money,
trade assets, or claim knowledge without evidence.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import os
import time
from pathlib import Path
from typing import Any

STATE_PATH = Path(os.getenv("BRAIN_DEVELOPMENT_STATE", "development_state.json"))


@dataclass(frozen=True)
class Domain:
    name: str
    category: str
    priority: int
    evidence_required: str


DOMAINS = [
    Domain("financial", "finance", 1, "tests + verified data"),
    Domain("banking", "finance", 2, "tests + primary sources"),
    Domain("markets", "finance", 2, "tests + current market data"),
    Domain("trade", "commerce", 1, "unit economics + market evidence"),
    Domain("crypto", "markets", 3, "risk tests + current data"),
    Domain("stocks", "markets", 3, "valuation tests + current data"),
    Domain("local_market", "commerce", 1, "Jordan market evidence"),
    Domain("global_market", "commerce", 2, "multi-market evidence"),
    Domain("mathematics", "science", 2, "problem tests"),
    Domain("statistics", "science", 2, "statistical tests"),
    Domain("computer_science", "technology", 1, "software tests"),
    Domain("cybersecurity", "technology", 2, "defensive tests"),
    Domain("science", "science", 4, "source-backed knowledge tests"),
    Domain("engineering", "engineering", 4, "calculation/simulation tests"),
    Domain("law_compliance", "governance", 2, "jurisdiction-specific primary sources"),
    Domain("communication", "humanities", 4, "quality tests"),
]


def _load() -> dict[str, Any]:
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save(data: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def assess() -> dict[str, Any]:
    """Return a conservative capability map.

    A domain is not marked mastered merely because it is listed. Existing
    code gives some domains implementation coverage, while current external
    evidence is still required for claims about live markets.
    """
    state = _load()
    mastered = set(state.get("mastered_domains", []))
    implemented = {
        "financial", "trade",
    }
    rows = []
    for domain in sorted(DOMAINS, key=lambda d: (d.priority, d.name)):
        status = "MASTERED" if domain.name in mastered else (
            "IMPLEMENTED_BASE" if domain.name in implemented else "NEEDS_EVIDENCE"
        )
        rows.append({**asdict(domain), "status": status})
    return {
        "timestamp": time.time(),
        "domains": rows,
        "mastered_count": len(mastered),
        "implemented_base_count": len(implemented),
        "evidence_gap_count": sum(x["status"] == "NEEDS_EVIDENCE" for x in rows),
    }


def next_development() -> dict[str, Any]:
    """Choose the highest-priority domain whose evidence is still missing."""
    assessment = assess()
    pending = [x for x in assessment["domains"] if x["status"] == "NEEDS_EVIDENCE"]
    choice = pending[0] if pending else None
    return {
        "status": "READY" if choice else "NO_PENDING_DOMAIN",
        "next": choice,
        "rule": "priority first; never claim mastery without evidence",
    }


def record_learning(domain: str, evidence: str, test_passed: bool) -> dict[str, Any]:
    """Record evidence-backed progress without granting permissions."""
    data = _load()
    history = data.setdefault("learning_history", [])
    entry = {
        "timestamp": time.time(),
        "domain": str(domain),
        "evidence": str(evidence),
        "test_passed": bool(test_passed),
    }
    history.append(entry)
    if test_passed:
        mastered = set(data.setdefault("mastered_domains", []))
        mastered.add(str(domain))
        data["mastered_domains"] = sorted(mastered)
    _save(data)
    return entry


def development_report() -> dict[str, Any]:
    report = assess()
    report["next_development"] = next_development()
    return report
