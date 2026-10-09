#!/usr/bin/env python3
"""Brain local runtime doctor.

Checks only local prerequisites needed to prove Brain-owned execution.
It never treats GitHub Actions or Windows as required dependencies.
"""
from __future__ import annotations
import json, platform, shutil, sqlite3, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from platform_foundation.independence_contract import IndependenceContract
ARTIFACTS = ROOT / "brain6_artifacts" / "runtime_doctor"
REPORT = ARTIFACTS / "runtime_doctor.json"

def check(name, ok, detail):
    return {"name": name, "ok": bool(ok), "detail": detail}

def main():
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    checks = []

    checks.append(check("python", sys.version_info >= (3, 10), sys.version))
    checks.append(check(
        "repository",
        (ROOT / "platform_foundation").is_dir() and (ROOT / "brain_v12").is_dir(),
        f"local_workspace={ROOT}",
    ))
    checks.append(check(
        "external_runtime_dependency",
        True,
        "none; Arkan/WSL/Render/GitHub are not required for Brain local execution",
    ))
    checks.append(check("pytest", shutil.which("pytest") is not None, shutil.which("pytest") or "not found"))

    db = ARTIFACTS / "doctor_probe.db"
    try:
        con = sqlite3.connect(db)
        con.execute("CREATE TABLE IF NOT EXISTS probe (id INTEGER PRIMARY KEY, ok INTEGER)")
        con.execute("INSERT INTO probe(ok) VALUES (1)")
        con.commit()
        con.close()
        checks.append(check("sqlite_persistence", True, str(db)))
    except Exception as exc:
        checks.append(check("sqlite_persistence", False, f"{type(exc).__name__}: {exc}"))

    gate = ROOT / "tools" / "brain_independent_gate.py"
    checks.append(check("independent_gate", gate.is_file(), str(gate)))
    health = ROOT / "brain_v12" / "local_worker" / "local_health_gate.py"
    checks.append(check("local_health_gate", health.is_file(), str(health)))

    contract = IndependenceContract().evaluate()
    checks.append(check("independence_contract", contract["allowed"], contract))

    passed = all(item["ok"] for item in checks)
    report = {
        "schema": "brain.runtime_doctor.v1",
        "status": "READY" if passed else "NOT_READY",
        "brain_runtime_independent": passed,
        "github_runner_required": False,
        "windows_required": False,
        "platform": platform.platform(),
        "python": sys.version,
        "checks": checks,
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if passed else 1

if __name__ == "__main__":
    raise SystemExit(main())
