"""Audit a downloaded Brain Windows real-boot artifact ZIP without trusting filenames alone.

The audit fails closed: installer/ISO/QEMU startup evidence is never accepted as a
completed Windows Server 2025 boot. This tool does not contact services or secrets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


REQUIRED = {
    "windows-boot-evidence.json",
    "windows-completion-gate.json",
    "windows-boot-proof.json",
    "windows-boot-phase.txt",
    "WINDOWS_BOOT_VERIFIED",
    "cloud-executor-gate.json",
}


def audit_artifact(artifact: Path, expected_run_id: str = "") -> dict:
    reasons: list[str] = []
    digest = hashlib.sha256()
    try:
        with artifact.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        with zipfile.ZipFile(artifact) as archive:
            by_name: dict[str, str] = {}
            for info in archive.infolist():
                if info.is_dir():
                    continue
                name = Path(info.filename).name
                if name in REQUIRED:
                    if name in by_name:
                        reasons.append("DUPLICATE_EVIDENCE_FILE:" + name)
                    by_name[name] = info.filename
            missing = sorted(REQUIRED - set(by_name))
            reasons.extend("ARTIFACT_FILE_MISSING:" + name for name in missing)

            def read_json(name: str) -> dict:
                if name not in by_name:
                    return {}
                try:
                    value = json.loads(archive.read(by_name[name]).decode("utf-8-sig"))
                    if not isinstance(value, dict):
                        raise ValueError("root is not an object")
                    return value
                except Exception:
                    reasons.append("ARTIFACT_JSON_INVALID:" + name)
                    return {}

            evidence = read_json("windows-boot-evidence.json")
            completion = read_json("windows-completion-gate.json")
            proof = read_json("windows-boot-proof.json")
            executor = read_json("cloud-executor-gate.json")
            phase = archive.read(by_name["windows-boot-phase.txt"]).decode("utf-8", "replace") if "windows-boot-phase.txt" in by_name else ""
            marker = archive.read(by_name["WINDOWS_BOOT_VERIFIED"]).decode("utf-8-sig", "replace").strip() if "WINDOWS_BOOT_VERIFIED" in by_name else ""

            if marker != "WINDOWS_BOOT_VERIFIED":
                reasons.append("GUEST_MARKER_INVALID")
            if "BOOT_PHASE=WINDOWS_INSTALLED_AND_BOOTED_FROM_DISK" not in phase:
                reasons.append("INSTALLED_DISK_PHASE_MISSING")
            if "BOOT_SOURCE=windows-installed-disk" not in phase:
                reasons.append("INSTALLED_DISK_PHASE_SOURCE_MISSING")
            if evidence.get("schema") != "BRAIN-WINDOWS-BOOT-EVIDENCE-1":
                reasons.append("GUEST_EVIDENCE_SCHEMA_INVALID")
            if evidence.get("status") != "WINDOWS_BOOT_VERIFIED":
                reasons.append("GUEST_EVIDENCE_STATUS_INVALID")
            guest = evidence.get("guest") or {}
            if guest.get("os") != "Windows Server 2025" or guest.get("boot_verified") is not True:
                reasons.append("GUEST_OS_BOOT_NOT_PROVEN")
            if evidence.get("boot_source") != "windows-installed-disk":
                reasons.append("BOOT_SOURCE_NOT_INSTALLED_DISK")
            if completion.get("verified") is not True or completion.get("status") != "WINDOWS_BOOT_VERIFIED":
                reasons.append("COMPLETION_GATE_NOT_PASSED")
            if proof.get("verified") is not True or proof.get("status") != "WINDOWS_BOOT_VERIFIED":
                reasons.append("BOOT_PROOF_NOT_PASSED")
            if executor.get("verified") is not True:
                reasons.append("CLOUD_EXECUTOR_GATE_NOT_PASSED")

            run_id = str(expected_run_id or proof.get("workflow_run_id") or "").strip()
            evidence_run_id = str((evidence.get("executor") or {}).get("workflow_run_id", "")).strip()
            proof_run_id = str(proof.get("workflow_run_id", "")).strip()
            if not run_id:
                reasons.append("EXPECTED_RUN_ID_MISSING")
            if evidence_run_id != run_id or proof_run_id != run_id:
                reasons.append("WORKFLOW_RUN_ID_MISMATCH")

    except (OSError, zipfile.BadZipFile) as exc:
        reasons.append("ARTIFACT_UNREADABLE:" + type(exc).__name__)
        run_id = str(expected_run_id or "").strip()

    reasons = list(dict.fromkeys(reasons))
    return {
        "schema": "brain.windows-boot-artifact-audit.v1",
        "status": "WINDOWS_BOOT_VERIFIED" if not reasons else "NO_GO",
        "verified": not reasons,
        "workflow_run_id": run_id or None,
        "artifact_sha256": digest.hexdigest(),
        "reasons": reasons,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_zip", type=Path)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--output", type=Path, default=Path("windows-artifact-audit.json"))
    args = parser.parse_args()
    result = audit_artifact(args.artifact_zip, args.run_id)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
