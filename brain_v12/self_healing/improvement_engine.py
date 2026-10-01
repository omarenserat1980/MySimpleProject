#!/usr/bin/env python3
"""Deterministic improvement discovery for the Brain self-healing loop.

This module never mutates source code. It discovers low-risk, evidence-backed
improvement opportunities and writes a machine-readable proposal. Actual code
changes remain behind the reversible code-repair agent and verification gate.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / ".brain" / "state"
HISTORY = STATE / "improvement_history.jsonl"
PROPOSAL = STATE / "current_improvement.json"

PY_ROOTS = tuple(
    x.strip() for x in os.getenv("BRAIN_REVIEW_ROOTS", "brain_v12,tests,scripts").split(",")
    if x.strip()
)
DIRECT_SCRIPT = re.compile(r'(?:["\'](?:python|python3)["\']|sys\.executable)\s*,\s*["\'][^"\']+\.py["\']')


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def git(args: list[str]) -> str:
    p = subprocess.run(["git", *args], cwd=ROOT, text=True,
                       capture_output=True, check=False)
    return p.stdout.strip()


def files() -> list[Path]:
    result: list[Path] = []
    for root in PY_ROOTS:
        base = ROOT / root
        if base.exists():
            result.extend(p for p in base.rglob("*.py") if p.is_file())
    return result


def discover() -> list[dict]:
    candidates: list[dict] = []

    # Package-invocation consistency: direct execution of package modules can
    # break imports when the repository root is not on sys.path.
    for path in files():
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for line_no, line in enumerate(content.splitlines(), 1):
            if DIRECT_SCRIPT.search(line) and "self_healing" in line:
                candidates.append({
                    "id": "package-invocation-consistency",
                    "priority": "high",
                    "file": str(path.relative_to(ROOT)),
                    "line": line_no,
                    "finding": line.strip(),
                    "proposal": "Prefer python -m package.module for package-internal tools.",
                    "risk": "low",
                })
                break

    # Evidence hygiene: ensure the review loop has persistent state files.
    required = [
        ".brain/state/review_loop_report.json",
        ".brain/state/verification_gate.json",
        ".brain/state/continuous_evolution_history.jsonl",
    ]
    missing = [p for p in required if not (ROOT / p).exists()]
    if missing:
        candidates.append({
            "id": "evidence-state-completeness",
            "priority": "medium",
            "finding": "Expected evidence files are absent in the current workspace.",
            "missing": missing,
            "proposal": "Ensure the active review cycle materializes its evidence records.",
            "risk": "low",
        })

    return candidates


def main() -> int:
    STATE.mkdir(parents=True, exist_ok=True)
    head = git(["rev-parse", "HEAD"])
    candidates = discover()
    result = {
        "schema": "brain-improvement-proposal/v1",
        "created_at": now(),
        "baseline_commit": head,
        "mode": "PROPOSAL_ONLY" if not os.getenv("BRAIN_CODE_GENERATOR_COMMAND") else "GENERATOR_ELIGIBLE",
        "candidate_count": len(candidates),
        "candidates": candidates,
    }
    PROPOSAL.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    with HISTORY.open("a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")
    print(json.dumps({
        "status": "CANDIDATES_FOUND" if candidates else "NO_SAFE_CANDIDATE",
        "candidate_count": len(candidates),
        "mode": result["mode"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
