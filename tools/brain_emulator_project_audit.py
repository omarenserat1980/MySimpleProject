#!/usr/bin/env python3
"""Read-only Electronic Brain project audit and Windows Server 2025 boot preflight.

This tool never provisions infrastructure, changes secrets, installs packages, or
starts a VM. It reports repository capabilities separately from live-host readiness.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
KEY_PATHS = [
    "PROJECT_MASTER_SPEC.md",
    "PROJECT_ROADMAP.md",
    "DECISIONS.md",
    "CHANGELOG.md",
    "README.md",
    "brain_v12/app.py",
    "brain_v12/brain/execution_gateway.py",
    "brain_v12/brain/windows_cloud_executor.py",
    "brain_v12/brain/windows_cloud_provider_factory.py",
    "brain_v12/brain/terraform_windows_cloud_provider.py",
    "brain_v12/brain/opennebula_windows_cloud_provider.py",
    "brain_v12/brain/windows_real_boot_qemu_adapter.py",
    "brain_v12/tools/brain_emulator_agent.py",
    "tools/brain_emulator_agent.py",
    ".github/workflows/brain-windows-real-boot.yml",
    "docs/WINDOWS_SERVER_2025_REAL_BOOT_RUNBOOK.md",
    "brain_v12/CLOUD_EXECUTOR_ACTIVATION.md",
]
PROJECT_AREAS = [
    "brain_v12/brain",
    "brain_v12/self_healing",
    "brain_v12/movie_summary_factory",
    "brain_v12/business",
    "brain_v12/economics",
    "brain_v12/web",
    "brain_v12/tests",
    "tools",
    ".github/workflows",
    "docs",
    "brain_emulator",
]
SECRET_ENV_NAMES = [
    "BRAIN_CLOUD_EXECUTOR_TOKEN",
    "BRAIN_CLOUD_EXECUTOR_REGISTRY_URL",
    "BRAIN_CLOUD_EXECUTOR_ATTESTATION_FILE",
    "BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64",
    "BRAIN_CLOUD_EXECUTOR_ID",
    "BRAIN_AUTHORITY_SIGNING_TOKEN",
    "BRAIN_WINDOWS_CONTROL_PLANE_URL",
    "BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY",
    "BRAIN_WINDOWS_CLOUD_PROVIDER",
    "BRAIN_WINDOWS_TERRAFORM_DIR",
    "BRAIN_WINDOWS_CLOUD_ALLOW_APPLY",
]
REQUIRED_BOOT_TOOLS = [
    "qemu-system-x86_64",
    "qemu-img",
    "xorriso",
    "wimlib-imagex",
    "mkfs.vfat",
    "mcopy",
    "terraform",
    "onevm",
    "onetemplate",
]
OVMF_PATHS = [
    "/usr/share/OVMF/OVMF_CODE_4M.fd",
    "/usr/share/OVMF/OVMF_VARS_4M.fd",
    "/usr/share/ovmf/OVMF_CODE.fd",
]


def run_version(command: list[str]) -> dict[str, Any]:
    try:
        p = subprocess.run(command, capture_output=True, text=True, timeout=8, check=False)
        output = (p.stdout or p.stderr).strip().splitlines()
        return {"available": p.returncode == 0, "version": output[0][:180] if output else ""}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "reason": type(exc).__name__}


def markdown_inventory(relative_path: str) -> dict[str, Any]:
    path = REPO_ROOT / relative_path
    if not path.is_file():
        return {"exists": False, "headings": [], "checked": 0, "pending": 0, "tasks": []}
    text = path.read_text(encoding="utf-8", errors="replace")
    headings = [line.strip("# ").strip() for line in text.splitlines() if line.startswith("#")]
    task_rows = re.findall(r"^\s*- \[([ xX])\] (.+)$", text, flags=re.MULTILINE)
    tasks = [{"done": mark.lower() == "x", "task": label.strip()} for mark, label in task_rows]
    return {
        "exists": True,
        "headings": headings,
        "checked": sum(1 for item in tasks if item["done"]),
        "pending": sum(1 for item in tasks if not item["done"]),
        "tasks": tasks,
    }


def audit() -> dict[str, Any]:
    key_paths = {
        path: {"exists": (REPO_ROOT / path).is_file()}
        for path in KEY_PATHS
    }
    areas = {}
    for rel in PROJECT_AREAS:
        path = REPO_ROOT / rel
        if path.is_dir():
            py_files = list(path.rglob("*.py"))
            files = [p for p in path.rglob("*") if p.is_file()]
            areas[rel] = {
                "exists": True,
                "files": len(files),
                "python_files": len(py_files),
            }
        else:
            areas[rel] = {"exists": False, "files": 0, "python_files": 0}

    roadmap = markdown_inventory("PROJECT_ROADMAP.md")
    master_spec = markdown_inventory("PROJECT_MASTER_SPEC.md")
    workflows_dir = REPO_ROOT / ".github/workflows"
    workflow_inventory = sorted(
        path.relative_to(REPO_ROOT).as_posix()
        for path in workflows_dir.rglob("*")
        if path.is_file()
    ) if workflows_dir.is_dir() else []
    tools = {name: run_version([name, "--version"]) for name in REQUIRED_BOOT_TOOLS}
    # QEMU versions can print to stderr; test existence independently from version exit code.
    for name in REQUIRED_BOOT_TOOLS:
        tools[name]["path"] = shutil.which(name)
        tools[name]["available"] = bool(tools[name]["path"])
    kvm = Path("/dev/kvm")
    ovmf = {p: Path(p).is_file() for p in OVMF_PATHS}
    env_presence = {name: bool(os.environ.get(name, "").strip()) for name in SECRET_ENV_NAMES}
    secret_values_disclosed = False

    boot_workflow = (REPO_ROOT / ".github/workflows/brain-windows-real-boot.yml").is_file()
    adapter = (REPO_ROOT / "brain_v12/brain/windows_real_boot_qemu_adapter.py").is_file()
    provider_factory = (REPO_ROOT / "brain_v12/brain/windows_cloud_provider_factory.py").is_file()
    selected_provider = os.environ.get("BRAIN_WINDOWS_CLOUD_PROVIDER", "").strip().lower()
    if not selected_provider:
        provider_configuration = "NOT_SET_QEMU_PATH_MAY_BE_USED"
    elif selected_provider not in {"terraform", "opennebula"}:
        provider_configuration = "UNSUPPORTED_PROVIDER"
    else:
        provider_configuration = selected_provider

    missing_required = [name for name in [
        "BRAIN_CLOUD_EXECUTOR_ID",
        "BRAIN_CLOUD_EXECUTOR_REGISTRY_URL",
        "BRAIN_CLOUD_EXECUTOR_TOKEN",
        "BRAIN_CLOUD_EXECUTOR_ATTESTATION_FILE",
        "BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64",
    ] if not env_presence[name]]
    missing_tools = [name for name in REQUIRED_BOOT_TOOLS[:6] if not tools[name]["available"]]
    kvm_ok = kvm.exists() and os.access(kvm, os.R_OK | os.W_OK)
    ovmf_ok = any(ovmf.values())

    blockers = []
    if not boot_workflow:
        blockers.append("REAL_BOOT_WORKFLOW_MISSING")
    if not adapter:
        blockers.append("QEMU_REAL_BOOT_ADAPTER_MISSING")
    if not provider_factory:
        blockers.append("WINDOWS_CLOUD_PROVIDER_FACTORY_MISSING")
    if provider_configuration == "UNSUPPORTED_PROVIDER":
        blockers.append("WINDOWS_CLOUD_PROVIDER_UNSUPPORTED")
    if missing_required:
        blockers.append("CLOUD_EXECUTOR_HOST_CONFIGURATION_MISSING")
    if missing_tools:
        blockers.append("QEMU_BOOT_TOOLING_MISSING")
    if not kvm_ok:
        blockers.append("KVM_UNAVAILABLE_OR_PERMISSION_DENIED")
    if not ovmf_ok:
        blockers.append("OVMF_FIRMWARE_MISSING")

    return {
        "schema": "electronic-brain.project-audit.v1",
        "repository_root": str(REPO_ROOT),
        "mode": "READ_ONLY",
        "host": {
            "system": platform.system(),
            "release": platform.release(),
            "architecture": platform.machine(),
            "python": platform.python_version(),
        },
        "project_purpose": "Evidence-first autonomous automation, execution, verification, recovery, media, device, knowledge, and economic outcome platform.",
        "project_areas": areas,
        "project_goals_and_roadmap": {
            "master_spec": master_spec,
            "roadmap": roadmap,
            "workflow_inventory": workflow_inventory,
        },
        "key_paths": key_paths,
        "boot_path": {
            "workflow_present": boot_workflow,
            "qemu_adapter_present": adapter,
            "provider_factory_present": provider_factory,
            "provider_configuration": provider_configuration,
            "provider_required_for_qemu_boot": False,
            "tools": tools,
            "dev_kvm_exists": kvm.exists(),
            "dev_kvm_read_write": kvm_ok,
            "ovmf_paths": ovmf,
            "local_environment_presence_only": env_presence,
            "missing_host_configuration_names": missing_required,
            "attestation_file_exists": bool(os.environ.get("BRAIN_CLOUD_EXECUTOR_ATTESTATION_FILE")) and Path(os.environ.get("BRAIN_CLOUD_EXECUTOR_ATTESTATION_FILE", "")).is_file(),
            "control_plane_configuration": {
                "status": "NOT_CHECKED_REMOTELY",
                "required_names": [
                    "BRAIN_EXECUTOR_ATTESTATION_SIGNING_KEY_B64",
                    "BRAIN_CLOUD_EXECUTOR_ENROLLMENTS_SHA256_JSON",
                    "BRAIN_CLOUD_EXECUTOR_HOST_BINDINGS_JSON",
                    "BRAIN_CLOUD_EXECUTOR_REGISTRY_DB",
                ],
                "note": "These belong on the Control Plane; this local audit must not read or print their values.",
            },
            "secret_values_disclosed": secret_values_disclosed,
            "blockers": blockers,
            "status": "READY_FOR_REVIEW" if not blockers else "BLOCKED",
        },
        "acceptance_rule": {
            "required": [
                "guest-generated windows-boot-evidence.json",
                "WINDOWS_BOOT_VERIFIED marker from guest evidence volume",
                "independent completion gate pass",
                "all evidence from the same workflow run",
            ],
            "qemu_started_or_workflow_green_is_not_boot_proof": True,
        },
        "limits": [
            "This is a local read-only audit, not a cloud provider API check.",
            "Environment variable presence does not prove validity, authorization, signature, or server-side configuration.",
            "A project path existing does not prove a service or Windows guest is running.",
            "No packages are installed and no VM or cloud resources are created.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON only")
    parser.add_argument("--output", help="write report JSON to this path")
    args = parser.parse_args()
    report = audit()
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        target = Path(args.output).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered + "\n", encoding="utf-8")
    print(rendered if args.json else (
        "ELECTRONIC BRAIN PROJECT AUDIT\n"
        f"Root: {report['repository_root']}\n"
        f"Host: {report['host']['system']} {report['host']['architecture']}\n"
        f"Windows cloud boot readiness: {report['boot_path']['status']}\n"
        "Blockers:\n" + "\n".join(f"- {x}" for x in report["boot_path"]["blockers"]) +
        "\n\nFull report:\n" + rendered
    ))
    return 0 if report["boot_path"]["status"] == "READY_FOR_REVIEW" else 2


if __name__ == "__main__":
    raise SystemExit(main())
