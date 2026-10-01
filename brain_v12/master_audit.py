#!/usr/bin/env python3
"""Evidence-first master audit for Electronic Brain.

This audit inventories implementation state without treating file existence as proof
of runtime completion. It emits a machine-readable evidence report.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / ".brain" / "state" / "master_audit.json"

REQUIRED_DOCS = [
    "PROJECT_MASTER_SPEC.md",
    "PROJECT_ROADMAP.md",
    "DECISIONS.md",
    "CHANGELOG.md",
    "README.md",
]
REQUIRED_MODULES = [
    "brain_v12/self_healing/supervisor.py",
    "brain_v12/self_healing/verification_gate.py",
    "brain_v12/self_healing/repair.py",
    "brain_v12/brain/brain_supervisor.py",
    "brain_v12/brain/autonomy_control_plane.py",
    "brain_v12/causal/causal_engine.py",
    "brain_v12/causal/runtime_bridge.py",
    "brain_v12/quran/quran_reasoning.py",
    "brain_v12/quran/complete_quran_builder.py",
    "brain_v12/quran/ayah_knowledge_pipeline.py",
    "brain_v12/quran/quran_knowledge_graph.py",
    "brain_v12/quran/quran_linguistic_ingest.py",
    "brain_v12/quran/quran_corpus_adapter.py",
    "brain_v12/quran/quran_layer_audit.py",
    "brain_v12/media_engine.py",
    "brain_v12/machine_cinematic_factory.py",
]

def exists(rel: str) -> bool:
    return (ROOT / rel).exists()

def run(cmd: list[str]) -> dict:
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "command": cmd,
        "exit_code": p.returncode,
        "stdout_tail": p.stdout[-4000:],
        "stderr_tail": p.stderr[-4000:],
    }

def main() -> int:
    REPORT.parent.mkdir(parents=True, exist_ok=True)

    workflows = sorted((ROOT / ".github" / "workflows").glob("*.y*ml")) if (ROOT / ".github" / "workflows").exists() else []
    docs = {p: exists(p) for p in REQUIRED_DOCS}
    modules = {p: exists(p) for p in REQUIRED_MODULES}

    report = {
        "schema": "brain-master-audit/v1",
        "principle": "file existence is not runtime completion",
        "docs": docs,
        "modules": modules,
        "workflow_count": len(workflows),
        "workflow_names": [p.name for p in workflows],
        "areas": {
            "self_healing": all(modules[p] for p in REQUIRED_MODULES[:3]),
            "supervisor": all(modules[p] for p in REQUIRED_MODULES[3:5]),
            "causal": all(modules[p] for p in REQUIRED_MODULES[5:7]),
            "quran": all(modules[p] for p in REQUIRED_MODULES[7:14]),
            "cinematic": all(modules[p] for p in REQUIRED_MODULES[14:]),
        },
        "runtime_checks": {},
    }

    for name, cmd in {
        "python_compile": [sys.executable, "-m", "compileall", "-q", "brain_v12"],
        "quran_layer_audit": [sys.executable, "brain_v12/quran/quran_layer_audit.py"],
        # Run as a package so imports such as `from brain_v12...` resolve in CI.\n        "v12_self_test": [sys.executable, "-m", "brain_v12.self_healing.self_test"],
    }.items():
        result = run(cmd)
        report["runtime_checks"][name] = result

    registry = ROOT / ".brain" / "quran" / "verse_registry.jsonl"
    if registry.exists():
        rows = [json.loads(x) for x in registry.read_text(encoding="utf-8").splitlines() if x.strip()]
        report["quran_registry"] = {
            "status": "VERIFIED" if len(rows) == 6236 and rows[0]["verse_key"] == "1:1" and rows[-1]["verse_key"] == "114:6" else "FAILED",
            "count": len(rows),
            "first": rows[0]["verse_key"] if rows else None,
            "last": rows[-1]["verse_key"] if rows else None,
        }
    else:
        report["quran_registry"] = {"status": "NOT_BUILT"}

    runtime_failed = [k for k, v in report["runtime_checks"].items() if v["exit_code"] != 0]
    report["status"] = "FAILED" if runtime_failed else "AUDITED"
    report["failed_checks"] = runtime_failed

    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("BRAIN_MASTER_AUDIT=" + report["status"])
    print("WORKFLOW_COUNT=" + str(len(workflows)))
    print("QURAN_REGISTRY=" + report["quran_registry"]["status"])
    if runtime_failed:
        print("FAILED_CHECKS=" + ",".join(runtime_failed))
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
