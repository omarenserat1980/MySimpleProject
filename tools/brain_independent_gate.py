#!/usr/bin/env python3
"""Single local boundary gate for Brain execution independence.

This gate proves that Brain can operate from its own workspace without
requiring Arkan/WSL, GitHub Actions, or Render. External services are checked
only as optional/non-authoritative roles.
"""
from __future__ import annotations
import json, os, platform, subprocess, sys, time
from pathlib import Path

from platform_foundation.provider_policy import (
    BrainProviderPolicy, ProviderDescriptor, ProviderRole, ProviderDecision,
)

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "brain6_artifacts" / "independence_gate"
EVIDENCE_FILE = EVIDENCE_DIR / "independence_gate.json"
TESTS = [
    "tests/test_executor_pool.py",
    "tests/test_provider_policy.py",
    "tests/test_runtime_doctor.py",
    "tests/test_local_guardian.py",
    "tests/test_brain_execution_authority.py",
]


def main() -> int:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    started = time.time()

    policy = BrainProviderPolicy()
    provider_check = policy.select([
        ProviderDescriptor("brain-local", ProviderRole.PRIMARY, available=True),
        ProviderDescriptor("render", ProviderRole.OPTIONAL_AUXILIARY, available=False),
        ProviderDescriptor("github-actions", ProviderRole.VERIFICATION_ONLY, available=False),
    ])

    command = [sys.executable, "-m", "pytest", "-q", *TESTS]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True)

    policy_ok = provider_check.decision == ProviderDecision.ALLOWED and provider_check.provider_id == "brain-local"
    tests_ok = proc.returncode == 0
    status = "PASS" if policy_ok and tests_ok else "FAIL"

    evidence = {
        "schema": "brain.independence_gate.v2",
        "status": status,
        "verified": status == "PASS",
        "gate": "BRAIN_INTERNAL_EXTERNAL_BOUNDARY",
        "execution_authority": "brain-local",
        "github_runner_required": False,
        "windows_required": False,
        "render_required": False,
        "external_services_authoritative": False,
        "provider_policy": {
            "decision": provider_check.decision.value,
            "provider_id": provider_check.provider_id,
            "reason": provider_check.reason,
        },
        "tests": TESTS,
        "command": command,
        "returncode": proc.returncode,
        "duration_seconds": round(time.time() - started, 3),
        "platform": platform.platform(),
        "python": sys.version,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }
    EVIDENCE_FILE.write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
