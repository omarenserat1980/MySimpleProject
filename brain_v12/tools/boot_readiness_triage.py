"""Evidence-first triage for the Windows Server 2025 real-boot path.

This tool summarizes existing gate reports; it does not create contracts,
change permissions, start VMs, or infer success from missing evidence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


GATES = (
    ("contract", "contract_gate", "BRAIN_WINDOWS_EXECUTION_CONTRACT_FILE_REQUIRED",
     "Obtain a real pre-issued contract from the authorized Brain Control Plane and stage it securely."),
    ("trusted_executor", "executor_gate", "TRUSTED_EXECUTOR_NOT_VERIFIED",
     "Repair the protected executor registry/attestation configuration; rerun the same-run executor gate."),
    ("runner", "runner_watch", "RUNNER_NOT_VERIFIED",
     "Fix the least-privilege runner-watch token permission, then require online labels and a passing execution probe."),
    ("boot_proof", "boot_proof", "WINDOWS_BOOT_NOT_PROVEN",
     "Run the protected real-boot workflow and require same-run installed-disk guest evidence."),
)


def _read(path: str | None) -> tuple[dict[str, Any] | None, str | None]:
    if not path:
        return None, "EVIDENCE_PATH_NOT_CONFIGURED"
    p = Path(path)
    try:
        obj = json.loads(p.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return None, "EVIDENCE_FILE_MISSING"
    except (OSError, json.JSONDecodeError):
        return None, "EVIDENCE_FILE_INVALID"
    if not isinstance(obj, dict):
        return None, "EVIDENCE_ROOT_NOT_OBJECT"
    return obj, None


def triage(paths: dict[str, str | None]) -> dict[str, Any]:
    blockers: list[dict[str, str]] = []
    gates: dict[str, dict[str, Any]] = {}
    for name, arg, code, action in GATES:
        report, error = _read(paths.get(arg))
        passed = error is None and report is not None and report.get("verified") is True
        # Runner watcher reports may use explicit PASS fields rather than verified.
        if name == "runner" and report is not None:
            passed = passed or (
                report.get("runner_online") is True
                and report.get("execution_probe") == "PASS"
                and report.get("runtime_surface") == "PASS"
            )
        if passed:
            gates[name] = {"status": "VERIFIED"}
        else:
            reason = error or (report.get("status") if report else None) or code
            gates[name] = {"status": "BLOCKED", "reason": str(reason)}
            blockers.append({
                "gate": name,
                "code": code if error is None else error,
                "reason": str(reason),
                "next_action": action,
            })

    return {
        "schema": "brain.boot-readiness-triage.v1",
        "status": "READY" if not blockers else "BLOCKED",
        "ready": not blockers,
        "gates": gates,
        "blockers": blockers,
        "policy": "Missing or invalid evidence is BLOCKED; no gate is inferred from another gate.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Triage Windows real-boot blockers from existing JSON evidence.")
    parser.add_argument("--contract-gate")
    parser.add_argument("--executor-gate")
    parser.add_argument("--runner-watch")
    parser.add_argument("--boot-proof")
    parser.add_argument("--output", default="boot-readiness-triage.json")
    args = parser.parse_args()
    result = triage({
        "contract_gate": args.contract_gate,
        "executor_gate": args.executor_gate,
        "runner_watch": args.runner_watch,
        "boot_proof": args.boot_proof,
    })
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
