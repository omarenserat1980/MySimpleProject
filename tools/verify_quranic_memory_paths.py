#!/usr/bin/env python3
"""Read-only smoke check for Quran-informed memory review paths.

Run from repository root:
    python tools/verify_quranic_memory_paths.py

This script imports the review helper and exercises representative inputs. It
does not connect to production, read credentials, or write to the Brain DB.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

# Ensure imports resolve from the repository root when invoked as a file.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    try:
        from brain_v12.brain.quranic_core.memory_guidance import principles, review_memory
    except Exception as exc:
        print(f"BLOCKED: cannot import Quranic memory guidance: {type(exc).__name__}: {exc}")
        return 2

    # Verify the production FastAPI entry point imports and mounts the router.
    app_path = REPO_ROOT / "brain_v12" / "app.py"
    try:
        app_source = app_path.read_text(encoding="utf-8")
        app_tree = ast.parse(app_source, filename=str(app_path))
    except Exception as exc:
        print(f"FAIL: cannot inspect application entry point: {type(exc).__name__}: {exc}")
        return 1

    imports_router = any(
        isinstance(node, ast.ImportFrom)
        and node.level == 1
        and node.module == "brain.quranic_core.api"
        and any(alias.name == "build_router" and alias.asname == "quranic_core_router" for alias in node.names)
        for node in ast.walk(app_tree)
    )
    mounts_router = any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "app"
        and node.func.attr == "include_router"
        and any(
            isinstance(arg, ast.Call)
            and isinstance(arg.func, ast.Name)
            and arg.func.id == "quranic_core_router"
            for arg in node.args
        )
        for node in ast.walk(app_tree)
    )
    if not imports_router or not mounts_router:
        print("FAIL: Quranic Core router is not imported and mounted by brain_v12/app.py")
        return 1

    items = principles()
    if not items:
        print("FAIL: no source-linked principles found")
        return 1
    if not all(item.get("reference") and item.get("theme") and item.get("engineering_principle") for item in items):
        print("FAIL: a principle is missing its reference/theme/principle")
        return 1

    evidence = review_memory("هذا دليل يحتاج تحقق من المصدر")
    if not evidence.get("ok") or evidence.get("memory_mutated") is not False:
        print("FAIL: evidence review did not preserve read-only contract")
        return 1
    if "evidence_and_verification" not in evidence.get("matched_review_lenses", []):
        print("FAIL: expected evidence/verification lens was not matched")
        return 1

    empty = review_memory("   ")
    if empty.get("ok") is not False or empty.get("status") != "EMPTY_MEMORY":
        print("FAIL: empty input did not fail closed")
        return 1

    uncertain = review_memory("This assumption is uncertain; check counterevidence.")
    if not uncertain.get("ok") or uncertain.get("memory_mutated") is not False:
        print("FAIL: uncertainty review did not preserve read-only contract")
        return 1

    print("PASS: production app source imports and mounts Quranic Core router")
    print("PASS: source-linked principles:", len(items))
    print("PASS: evidence, uncertainty, and empty-input paths")
    print("PASS: read-only contract; no operational memory was changed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
