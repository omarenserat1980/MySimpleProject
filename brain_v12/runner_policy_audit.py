"""Static guard for Brain execution workflows.

The audit is intentionally narrow: Brain autonomy/base-expansion workflows must
target the Brain-owned self-hosted label and may not contain GitHub-hosted
ubuntu runners. This prevents a future edit from silently restoring external
execution.
"""
from __future__ import annotations
from pathlib import Path
import re

PROTECTED = ("",)

def audit_workflows(root: Path) -> list[str]:
    findings: list[str] = []
    for path in sorted((root / ".github" / "workflows").glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        if re.search(r"runs-on:\s*ubuntu-[^\n]+", text):
            findings.append(f"{path}: github-hosted runner is forbidden")
        if "runs-on: [self-hosted, brain-runner]" not in text:
            findings.append(f"{path}: missing Brain runner target")
    return findings
