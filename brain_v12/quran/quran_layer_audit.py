#!/usr/bin/env python3
"""End-to-end audit for the BRAIN Quran knowledge layer."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run(module: str) -> None:
    p = subprocess.run([sys.executable, "-m", module], cwd=ROOT, capture_output=True, text=True)
    if p.returncode:
        print(p.stdout)
        print(p.stderr)
        raise SystemExit(p.returncode)


def main() -> int:
    modules = [
        "brain_v12.quran.quran_reasoning",
        "brain_v12.quran.ayah_knowledge_pipeline",
        "brain_v12.quran.quran_knowledge_graph",
    ]
    for module in modules:
        run(module)

    registry = ROOT / ".brain" / "quran" / "verse_registry.jsonl"
    if registry.exists():
        rows = [json.loads(x) for x in registry.read_text(encoding="utf-8").splitlines() if x.strip()]
        assert len(rows) == 6236
        assert rows[0]["verse_key"] == "1:1"
        assert rows[-1]["verse_key"] == "114:6"
        registry_status = "PASS"
    else:
        registry_status = "NOT_BUILT_IN_REPO"

    evidence = {
        "quran_reasoning_guard": "PASS",
        "ayah_knowledge_pipeline": "PASS",
        "knowledge_graph": "PASS",
        "registry": registry_status,
        "policy": "text/linguistics/tafsir/evidence/hypothesis remain separate",
    }
    out = ROOT / ".brain" / "state" / "quran_layer_audit.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("QURAN_LAYER_AUDIT=PASS")
    print("QURAN_REASONING_GUARD=PASS")
    print("QURAN_AYAH_KNOWLEDGE_PIPELINE=PASS")
    print("QURAN_KNOWLEDGE_GRAPH=PASS")
    print("QURAN_REGISTRY=" + registry_status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
