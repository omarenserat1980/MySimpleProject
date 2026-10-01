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
    changed = False
    output = []
    for line in old.splitlines(keepends=True):
        match = TARGET.search(line)
        if match and "self_healing" in line and "python" in line:
            module = match.group(2).replace("/", ".")
            replacement = '"-m", "' + module + '"'
            new_line = line[:match.start()] + replacement + line[match.end():]
            changed = changed or new_line != line
            output.append(new_line)
        else:
            output.append(line)

    if not changed:
        print("NATIVE_GENERATOR_NO_APPLICABLE_CHANGE")
        return 2

    patch = "".join(difflib.unified_diff(
        old.splitlines(keepends=True),
        "".join(output).splitlines(keepends=True),
        fromfile="a/" + path,
        tofile="b/" + path,
    ))
    if not patch.strip():
        print("NATIVE_GENERATOR_EMPTY_PATCH")
        return 2
    print(patch, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
