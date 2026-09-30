"""Static guard for Brain Cloud-only production policy."""
from __future__ import annotations
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]

RULES = [
    re.compile(r"(?i)(TERMUX_AGENT_KEY|TERMUX_AGENT_KEY_SHA256)\s*[:=]"),
    re.compile(r"""(?i)BRAIN_TERMUX_REQUIRED\s*[:=]\s*["']?1"""),
    re.compile(r"""(?i)BRAIN_DEVICE_EXECUTION_ENABLED\s*[:=]\s*["']?1"""),
]

SCAN_ROOTS = ("brain_v12", "cloud", ".github/workflows")
EXTS = {".py", ".yml", ".yaml", ".sh", ".cs", ".json"}

def main() -> int:
    violations = []
    for base in SCAN_ROOTS:
        p = ROOT / base
        if not p.exists():
            continue
        for f in p.rglob("*"):
            if not f.is_file() or f.suffix.lower() not in EXTS:
                continue
            text = f.read_text(encoding="utf-8", errors="ignore")
            for rule in RULES:
                for m in rule.finditer(text):
                    line = text.count("\n", 0, m.start()) + 1
                    violations.append({
                        "file": str(f.relative_to(ROOT)),
                        "line": line,
                        "rule": rule.pattern,
                    })
    if violations:
        print({"status": "FAILED", "violations": violations})
        return 1
    print({"status": "VERIFIED", "policy": "cloud-only"})
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
