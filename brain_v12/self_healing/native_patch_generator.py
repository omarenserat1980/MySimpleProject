#!/usr/bin/env python3
"""Native deterministic Brain patch generator.

Handles only the explicitly supported low-risk package-invocation finding.
It emits a unified patch and never applies it.
"""
from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROPOSAL = ROOT / ".brain" / "state" / "current_improvement.json"
TARGET = re.compile(r'(["\'])(brain_v12/(?:[A-Za-z0-9_]+/)*[A-Za-z0-9_]+)\.py\1')


def build_patch(old: str, path: str, line_no: int, finding: str) -> str | None:
    lines = old.splitlines(keepends=True)
    if line_no < 1 or line_no > len(lines):
        return None
    line = lines[line_no - 1]
    if finding and finding.strip() != line.strip():
        return None
    if "self_healing" not in line or "python" not in line:
        return None
    match = TARGET.search(line)
    if not match:
        return None
    module = match.group(2).replace("/", ".")
    replacement = '"-m", "' + module + '"'
    new_line = line[:match.start()] + replacement + line[match.end():]
    if new_line == line:
        return None
    new_lines = list(lines)
    new_lines[line_no - 1] = new_line
    return "".join(difflib.unified_diff(lines, new_lines, fromfile="a/" + path, tofile="b/" + path))


def main() -> int:
    if not PROPOSAL.is_file():
        print("NATIVE_GENERATOR_NO_PROPOSAL")
        return 2
    data = json.loads(PROPOSAL.read_text(encoding="utf-8"))
    candidate = next((c for c in data.get("candidates", [])
                      if c.get("id") == "package-invocation-consistency"), None)
    if not candidate:
        print("NATIVE_GENERATOR_NO_SUPPORTED_CANDIDATE")
        return 2

    path = str(candidate["file"])
    target = ROOT / path
    if not target.is_file():
        print("NATIVE_GENERATOR_TARGET_NOT_FOUND")
        return 2

    old = target.read_text(encoding="utf-8")
    line_no = int(candidate.get("line", 0) or 0)
    finding = str(candidate.get("finding", ""))
    patch = build_patch(old, path, line_no, finding)
    if patch is None:
        print("NATIVE_GENERATOR_CANDIDATE_MISMATCH")
        return 2

    if not patch.strip():
        print("NATIVE_GENERATOR_EMPTY_PATCH")
        return 2
    print(patch, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
