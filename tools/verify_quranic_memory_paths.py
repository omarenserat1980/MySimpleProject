#!/usr/bin/env python3
"""Read-only smoke check for Quran-informed memory review paths.

Run from repository root:
    python tools/verify_quranic_memory_paths.py

This script imports the review helper and exercises representative inputs. It
does not connect to production, read credentials, or write to the Brain DB.
"""
from __future__ import annotations

import sys


def main() -> int:
    try:
        from brain_v12.brain.quranic_core.memory_guidance import principles, review_memory
    except Exception as exc:
        print(f"BLOCKED: cannot import Quranic memory guidance: {type(exc).__name__}: {exc}")
        return 2

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

    print("PASS: source-linked principles:", len(items))
    print("PASS: evidence, uncertainty, and empty-input paths")
    print("PASS: read-only contract; no operational memory was changed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
