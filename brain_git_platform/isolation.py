from __future__ import annotations

import re
from pathlib import Path


FORBIDDEN = (
    r"github\.com",
    r"api\.github\.com",
    r"PyGithub",
    r"GITHUB_TOKEN",
)


def scan_runtime_tree(root: Path) -> list[str]:
    findings: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in {".py", ".json", ".toml", ".yaml", ".yml"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in FORBIDDEN:
            if re.search(pattern, text, flags=re.IGNORECASE):
                findings.append(f"{path}:{pattern}")
    return findings
