"""Static guard for Brain Cloud-only production policy."""
from __future__ import annotations
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
FORBIDDEN=("TERMUX_AGENT_KEY","TERMUX_AGENT_KEY_SHA256","termux deployment","phone ssh key")
PRODUCTION_DIRS=("brain_v12","cloud",".github/workflows")

def main()->int:
    violations=[]
    for base in PRODUCTION_DIRS:
        p=ROOT/base
        if not p.exists(): continue
        for f in p.rglob("*"):
            if not f.is_file() or f.suffix.lower() not in {".py",".yml",".yaml",".sh",".md",".cs",".json"}: continue
            text=f.read_text(encoding="utf-8",errors="ignore").lower()
            for token in FORBIDDEN:
                if token.lower() in text and f.name!="CLOUD_ONLY_POLICY.md":
                    violations.append({"file":str(f.relative_to(ROOT)),"token":token})
    if violations:
        print({"status":"FAILED","violations":violations})
        return 1
    print({"status":"VERIFIED","policy":"cloud-only"})
    return 0

if __name__=="__main__": raise SystemExit(main())
