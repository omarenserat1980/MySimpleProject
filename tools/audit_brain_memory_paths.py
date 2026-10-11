#!/usr/bin/env python3
"""Read-only audit of Electronic Brain V12 memory-related code paths.

The script does not modify source files, databases, environment variables, or
production services. Run from the repository root:
    python tools/audit_brain_memory_paths.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEARCH_ROOTS = (ROOT / "brain_v12", ROOT / "docs")
PATTERNS = {
    "memory_store": re.compile(r"MemoryStore|class\s+.*Memory|memory\.read|memory\.write", re.I),
    "sqlite_paths": re.compile(r"sqlite3|\.db\b|\.sqlite\b|connect\(", re.I),
    "api_routes": re.compile(r"@(?:app|router)\.(?:get|post|put|patch|delete)\([^\n]*(?:memory|learn|chat|quran|قرآن)", re.I),
    "quran_references": re.compile(r"qur['’]?an|quran|قرآن|آية|آيات|سورة|سور", re.I),
}
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules"}
TEXT_SUFFIXES = {".py", ".md", ".txt", ".json", ".yml", ".yaml", ".toml", ".html", ".js"}


def iter_files():
    for base in SEARCH_ROOTS:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            yield path


def main():
    report = {
        "audit": "brain-memory-paths",
        "mode": "read-only",
        "repository_root": str(ROOT),
        "files_scanned": 0,
        "findings": [],
        "limitations": [
            "Static text scan only; it does not prove a route is mounted or exercised at runtime.",
            "Quran-related references are reported for human review; no religious text is generated or altered.",
        ],
    }
    for path in sorted(iter_files()):
        report["files_scanned"] += 1
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError):
            continue
        for number, line in enumerate(lines, 1):
            for category, pattern in PATTERNS.items():
                if pattern.search(line):
                    report["findings"].append({
                        "category": category,
                        "path": path.relative_to(ROOT).as_posix(),
                        "line": number,
                        "excerpt": line.strip()[:240],
                    })
    report["summary"] = {
        category: sum(1 for item in report["findings"] if item["category"] == category)
        for category in PATTERNS
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
