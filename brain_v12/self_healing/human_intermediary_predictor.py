#!/usr/bin/env python3
"""Predict and safely continue the user's observed project-intermediary behavior.

This is an operational model, not a psychological or sensitive-personality model.
It learns only from repository-visible engineering behavior: commit messages,
roadmap completion, verification language, failures, and recovery patterns.

Contract:
  observe -> predict -> choose_next_safe_step -> execute_read_only_evidence ->
  verify -> persist_monotonic_state

It never edits production code, prompts, permissions, finances, publishing state,
or roadmap completion merely because a prediction was made.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / "brain_v12" / "state"
STATE_FILE = STATE_DIR / "human_intermediary_state.json"
REPORT_FILE = STATE_DIR / "human_intermediary_prediction.json"

REPO = os.getenv("GITHUB_REPOSITORY", "omarenserat1980/MySimpleProject")
API = "https://api.github.com"

# Explicitly bounded operational signals observed in this project history.
SIGNALS = {
    "continue_after_success": ("continue", "next", "اكمل", "نفذ", "follow", "advance"),
    "evidence_first": ("verify", "verification", "evidence", "gate", "qc", "artifact"),
    "repair_then_verify": ("fix", "repair", "harden", "recovery", "self-heal", "self healing"),
    "iterative_ci": ("ci", "workflow", "test", "pytest", "actions"),
    "free_first": ("no-pay", "free", "open-source", "oss", "without render"),
    "regression_avoidance": ("regression", "monotonic", "guard", "fail-closed"),
}

PHASE_TASKS: dict[int, list[str]] = {
    0: ["commercial outcome architecture"],
    1: [
        "failed tasks emit diagnostic evidence before workflow termination",
    ],
    2: [
        "watch recent workflow runs automatically",
        "fetch failed job logs and artifacts",
        "classify failures",
        "select a bounded repair strategy",
        "apply only approved repair scopes",
        "commit repair",
        "rerun affected workflow",
        "verify result and record evidence",
        "stop after bounded attempts",
    ],
}

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

def run_git(*args: str) -> str:
    p = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=False)
    return p.stdout

def roadmap() -> str:
    return (ROOT / "PROJECT_ROADMAP.md").read_text(encoding="utf-8", errors="ignore")

def parse_roadmap_tasks(text: str) -> dict[int, list[tuple[bool, str]]]:
    out: dict[int, list[tuple[bool, str]]] = {}
    phase = None
    for line in text.splitlines():
        m = re.match(r"## Phase (\d+)", line)
        if m:
            phase = int(m.group(1))
            out.setdefault(phase, [])
            continue
        if phase is not None:
            m = re.match(r"\s*- \[([ xX])\] (.+)", line)
            if m:
                out[phase].append((m.group(1).lower() == "x", m.group(2).strip()))
    return out

def history_messages(limit: int = 120) -> list[str]:
    raw = run_git("log", f"-n{limit}", "--pretty=format:%s")
    return [x.strip() for x in raw.splitlines() if x.strip()]

def infer_signals(messages: list[str]) -> dict[str, Any]:
    corpus = "\n".join(messages).lower()
    scores = {}
    for name, terms in SIGNALS.items():
        hits = [t for t in terms if t.lower() in corpus]
        scores[name] = {"hits": len(hits), "evidence_terms": hits}
    return scores

def api_get(path: str) -> dict[str, Any]:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if not token:
        return {"available": False, "reason": "no_github_token"}
    req = urllib.request.Request(
        API + path,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + token,
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return {"available": True, "data": json.load(resp)}
    except Exception as exc:
        return {"available": False, "reason": f"api_error:{type(exc).__name__}"}

def observe_actions() -> dict[str, Any]:
    result = api_get(f"/repos/{REPO}/actions/runs?branch=main&per_page=20")
    if not result.get("available"):
        return result
    runs = result.get("data", {}).get("workflow_runs", [])
    compact = [{
        "id": r.get("id"),
        "name": r.get("name"),
        "status": r.get("status"),
        "conclusion": r.get("conclusion"),
        "head_sha": r.get("head_sha"),
        "run_attempt": r.get("run_attempt"),
        "created_at": r.get("created_at"),
        "updated_at": r.get("updated_at"),
        "html_url": r.get("html_url"),
    } for r in runs]
    return {
        "available": True,
        "run_count": len(compact),
        "failed_count": sum(1 for r in compact if r["conclusion"] == "failure"),
        "runs": compact,
    }

def choose_frontier(parsed: dict[int, list[tuple[bool, str]]]) -> tuple[int, str, int]:
    # Phase order is monotonic. Phase 0 is complete, Phase 1 has one remaining
    # foundation item, then Phase 2 becomes active. We intentionally select the
    # earliest incomplete item so the predictor cannot skip prerequisites.
    for phase in sorted(parsed):
        tasks = parsed[phase]
        for index, (done, task) in enumerate(tasks):
            if not done:
                return phase, task, index
    return max(parsed or {0: []}), "all roadmap tasks currently marked complete", 0

def normalize_task(task: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", task.lower()).strip()

def safe_action_for(task: str, actions: dict[str, Any]) -> dict[str, Any]:
    t = normalize_task(task)
    if "watch recent workflow runs" in t:
        return {
            "id": "OBSERVE_RECENT_WORKFLOW_RUNS",
            "mode": "read_only",
            "executed": bool(actions.get("available")),
            "verification": "actions_snapshot_available" if actions.get("available") else "token_required",
        }
    if "fetch failed job logs" in t:
        return {
            "id": "PREPARE_FAILED_JOB_LOG_COLLECTION",
            "mode": "read_only",
            "executed": False,
            "verification": "requires_a_failed_run_from_the_observation_snapshot",
        }
    if "classify failures" in t:
        return {
            "id": "CLASSIFY_OBSERVED_FAILURES",
            "mode": "read_only",
            "executed": False,
            "verification": "requires_failure_evidence",
        }
    if "repair strategy" in t:
        return {
            "id": "SELECT_BOUNDED_REPAIR_STRATEGY",
            "mode": "plan_only",
            "executed": False,
            "verification": "requires_classified_failure_and_repair_scope",
        }
    return {
        "id": "HOLD_FOR_VERIFIED_PREREQUISITE",
        "mode": "fail_closed",
        "executed": False,
        "verification": "no_automatic_code_change_without_evidence",
    }

def load_state() -> dict[str, Any]:
    if not STATE_FILE.is_file():
        return {"schema": "brain-human-intermediary-state/v1", "max_phase": -1, "max_step": -1}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"schema": "brain-human-intermediary-state/v1", "max_phase": -1, "max_step": -1, "state_recovery": "invalid_state"}

def persist_monotonic(state: dict[str, Any], phase: int, step: int, report: dict[str, Any]) -> dict[str, Any]:
    old_phase = int(state.get("max_phase", -1))
    old_step = int(state.get("max_step", -1))
    regression = (phase < old_phase) or (phase == old_phase and step < old_step)
    if regression:
        phase, step = old_phase, old_step
    new_state = {
        "schema": "brain-human-intermediary-state/v1",
        "updated_at": now(),
        "max_phase": phase,
        "max_step": step,
        "regression_blocked": regression,
        "last_prediction": report["prediction"],
    }
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(new_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return new_state

def build_report() -> dict[str, Any]:
    parsed = parse_roadmap_tasks(roadmap())
    messages = history_messages()
    signals = infer_signals(messages)
    phase, task, step = choose_frontier(parsed)
    actions = observe_actions()

    # User-facing behavior is represented only as an operational continuation
    # profile. No sensitive traits or psychological diagnosis are inferred.
    profile = {
        "name": "HUMAN_INTERMEDIARY_OPERATIONAL_PROFILE",
        "prediction": [
            "continue from the current verified frontier rather than restart",
            "prefer evidence/gates before declaring completion",
            "repair a concrete failure before opening an unrelated new branch",
            "advance in small verified steps and preserve successful state",
            "prefer free/open-source paths when technically viable",
        ],
        "basis": {
            "repository_history_commits_sampled": len(messages),
            "signals": signals,
        },
    }

    action = safe_action_for(task, actions)
    state = load_state()
    report = {
        "schema": "brain-human-intermediary-prediction/v1",
        "created_at": now(),
        "source_of_truth": "GitHub repository history + roadmap + observable Actions evidence",
        "current_frontier": {"phase": phase, "step": step, "task": task},
        "predicted_user_behavior": profile,
        "next_safe_action": action,
        "actions_observation": actions,
        "anti_regression": {
            "policy": "monotonic_progress_only",
            "previous_max_phase": state.get("max_phase", -1),
            "previous_max_step": state.get("max_step", -1),
        },
        "execution_contract": {
            "automatic": True,
            "read_only_observation_allowed": True,
            "automatic_production_code_mutation": False,
            "automatic_prompt_mutation": False,
            "automatic_financial_or_external_side_effects": False,
            "success_requires_evidence": True,
        },
    }
    report["state"] = persist_monotonic(state, phase, step, report)
    return report

def main() -> int:
    report = build_report()
    REPORT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
