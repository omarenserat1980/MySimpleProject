#!/usr/bin/env python3
"""Predict future Brain evolution opportunities before failures occur.

The engine converts current architecture, dependency usage, prior failures and
missing runtime capabilities into a bounded, evidence-backed evolution plan.
It never treats a prediction as success: every proposed change must pass the
existing repair and verification gate before persistence.
"""
from __future__ import annotations

import ast
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / ".brain" / "state"
PLAN = STATE / "future_evolution_plan.json"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(module: str) -> tuple[int, str]:
    p = subprocess.run(
        [sys.executable, "-m", module],
        cwd=ROOT, text=True, capture_output=True, timeout=60,
    )
    return p.returncode, (p.stdout + "\n" + p.stderr)[-12000:]


def imports_from_runtime() -> list[str]:
    found: set[str] = set()
    for path in (ROOT / "brain_v12").rglob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                found.add(node.module.split(".")[0])
    return sorted(found)


def runtime_predictions() -> list[dict]:
    # Standard-library modules are deliberately excluded.
    stdlib = set(sys.stdlib_module_names)
    external = [x for x in imports_from_runtime() if x not in stdlib]
    checks = []
    for name in external:
        try:
            __import__(name)
            available = True
        except Exception:
            available = False
        checks.append({
            "type": "runtime_dependency",
            "id": f"dependency:{name}",
            "prediction": "dependency_missing" if not available else "dependency_ready",
            "risk": "high" if not available else "low",
            "evidence": "importable" if available else "not_importable_in_current_runtime",
        })
    return checks


def recent_failures() -> list[dict]:
    path = STATE / "continuous_evolution_history.jsonl"
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()[-20:]:
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if item.get("status") != "VERIFIED":
            rows.append({
                "type": "recurring_failure",
                "id": "cycle_failure",
                "prediction": "repeat_failure_until_root_cause_removed",
                "risk": "high",
                "evidence": {
                    "cycle": item.get("cycle"),
                    "review_exit_code": item.get("review_exit_code"),
                    "repair_exit_code": item.get("repair_exit_code"),
                },
            })
    return rows


def predict() -> dict:
    STATE.mkdir(parents=True, exist_ok=True)
    predictive_code, predictive_output = run("brain_v12.self_healing.predictive_failure_engine")
    improvement_code, improvement_output = run("brain_v12.self_healing.improvement_engine")

    predictions = runtime_predictions() + recent_failures()
    if predictive_code != 0:
        predictions.append({
            "type": "predictive_engine_failure",
            "id": "predictive-engine",
            "prediction": "prediction_engine_itself_needs_repair",
            "risk": "high",
            "evidence": predictive_output[-4000:],
        })

    plan = {
        "schema": "brain-future-evolution/v1",
        "created_at": now(),
        "status": "PREDICTIONS_READY" if predictions else "NO_PREDICTED_RISK",
        "objective": "predict -> prevent -> evolve -> verify -> learn -> repeat",
        "predicted_development_count": len(predictions),
        "predictions": predictions,
        "evidence": {
            "predictive_failure_engine_exit": predictive_code,
            "improvement_engine_exit": improvement_code,
            "predictive_output": predictive_output[-6000:],
            "improvement_output": improvement_output[-6000:],
        },
        "execution_policy": {
            "auto_execute": True,
            "allowed_change_surface": ["brain_v12", "tests", "scripts"],
            "required_after_change": ["compile", "self_test", "verification_gate"],
            "unverified_changes_allowed": False,
            "rollback_on_failed_gate": True,
        },
    }
    PLAN.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(plan, ensure_ascii=False))
    return plan


def main() -> int:
    predict()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
