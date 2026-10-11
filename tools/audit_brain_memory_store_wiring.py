#!/usr/bin/env python3
"""Focused static audit of Brain V12 SQLite memory-store wiring.

Read-only: checks source-code configuration and ordering, not runtime DB contents.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "brain_v12" / "app.py"
RUNTIME_PATHS = ROOT / "brain_v12" / "runtime_paths.py"
MEMORY_MODULE = ROOT / "brain_v12" / "brain" / "memory.py"


def audit_texts(app_text: str, runtime_text: str, memory_text: str) -> dict:
    setup = app_text.find("configure_runtime_paths()")
    store_init = app_text.find("store=MemoryStore(")
    checks = {
        "runtime_paths_initializer_imported": "from .runtime_paths import configure_runtime_paths" in app_text,
        "runtime_paths_configured_before_store_init": setup >= 0 and store_init >= 0 and setup < store_init,
        "app_store_path_uses_brain_db": bool(re.search(r"MemoryStore\(os\.getenv\(['\"]BRAIN_DB['\"]", app_text)),
        "runtime_defaults_brain_db": bool(re.search(r"['\"]BRAIN_DB['\"]\s*:\s*runtime_home\s*/\s*['\"]brain_v12\.db['\"]", runtime_text)),
        "runtime_preserves_explicit_brain_db": "os.environ.setdefault(name, str(default_path.resolve()))" in runtime_text and 'if name not in explicit:' in runtime_text,
        "memory_store_uses_sqlite": "sqlite3.connect(self.path)" in memory_text,
    }
    return {
        "audit": "brain-memory-store-wiring",
        "mode": "read-only-static",
        "checks": checks,
        "passed": sum(checks.values()),
        "total": len(checks),
        "failed_checks": [name for name, passed in checks.items() if not passed],
        "limitations": [
            "Checks source text only; does not inspect live environment variables or production database.",
            "A passing result proves expected code patterns/order, not successful persistence at runtime.",
        ],
    }


def main() -> None:
    report = audit_texts(
        APP.read_text(encoding="utf-8"),
        RUNTIME_PATHS.read_text(encoding="utf-8"),
        MEMORY_MODULE.read_text(encoding="utf-8"),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["failed_checks"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
