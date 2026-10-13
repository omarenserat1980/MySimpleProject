#!/usr/bin/env python3
"""Read-only preflight for a self-hosted Electronic Brain OpenNebula cloud.

This tool inspects the current Linux host and OpenNebula CLI. It never installs
packages, creates VMs, changes services, or applies cloud infrastructure.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
from pathlib import Path
from typing import Any

MIN_RAM_GIB = 8
MIN_FREE_DISK_GIB = 40


def check(name: str, ok: bool, detail: str, required: bool = True) -> dict[str, Any]:
    return {"name": name, "ok": bool(ok), "required": required, "detail": detail}


def main() -> int:
    checks: list[dict[str, Any]] = []
    is_linux = platform.system() == "Linux"
    arch = platform.machine().lower()
    is_x86_64 = arch in {"x86_64", "amd64"}
    checks.append(check("linux_host", is_linux, platform.platform()))

    # Arkan is forbidden for Huda; reject known Arkan host identity strings.
    hostname = platform.node().strip().lower()
    forbidden_tokens = ("arkan", "ark-an")
    identity_ok = not any(token in hostname for token in forbidden_tokens)
    checks.append(check("huda_host_identity_not_arkan", identity_ok,
                        "host identity accepted (hostname redacted)" if identity_ok else "ARKAN_FORBIDDEN: host hostname matches a forbidden Arkan identity"))
    checks.append(check("x86_64_architecture", is_x86_64, arch))

    mem_total_kib = 0
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                mem_total_kib = int(line.split()[1])
                break
    except (OSError, ValueError, IndexError):
        pass
    ram_gib = mem_total_kib / 1024 / 1024
    checks.append(check("host_ram", ram_gib >= MIN_RAM_GIB, f"{ram_gib:.2f} GiB; required >= {MIN_RAM_GIB} GiB"))

    try:
        disk = shutil.disk_usage(Path.cwd())
        free_gib = disk.free / (1024 ** 3)
    except OSError as exc:
        free_gib = 0
        disk_error = str(exc)
    else:
        disk_error = ""
    checks.append(check("free_disk", free_gib >= MIN_FREE_DISK_GIB,
                        f"{free_gib:.2f} GiB free on the current working filesystem; required >= {MIN_FREE_DISK_GIB} GiB" + (f"; {disk_error}" if disk_error else "")))

    kvm = Path("/dev/kvm")
    checks.append(check("kvm_device", kvm.exists() and os.access(kvm, os.R_OK | os.W_OK),
                        f"{kvm} exists and is accessible" if kvm.exists() else f"{kvm} is missing"))
    for binary in ("onevm", "onetemplate"):
        path = shutil.which(binary)
        checks.append(check(f"cli_{binary}", bool(path), path or f"{binary} not found in PATH"))

    endpoint = os.environ.get("ONE_XMLRPC", "").strip()
    # Never echo the endpoint: it may contain credentials or sensitive query parameters.
    checks.append(check("opennebula_endpoint", bool(endpoint),
                        "ONE_XMLRPC configured (value redacted)" if endpoint else "ONE_XMLRPC is unset; configure the OpenNebula XML-RPC endpoint"))
    user = os.environ.get("ONE_AUTH", "").strip()
    auth_file = Path(user.split(":", 1)[0]).expanduser() if ":" not in user and user else None
    auth_configured = bool(user) and (":" in user or (auth_file is not None and auth_file.is_file()))
    checks.append(check("opennebula_auth", auth_configured,
                        "ONE_AUTH configured" if auth_configured else "Set ONE_AUTH securely or configure ~/.one/one_auth; do not commit credentials"))

    required = [item for item in checks if item["required"]]
    result = {
        "schema_version": 1,
        "component": "electronic-brain-huda-cloud-preflight",
        "cloud_name": "هدى",
        "cloud_slug": "huda",
        "mode": "read_only",
        "status": "READY_FOR_REVIEW" if all(item["ok"] for item in required) else "BLOCKED",
        "provisioned": False,
        "vm_created": False,
        "checks": checks,
        "next_step": "Review every check, configure OpenNebula and a Windows Server 2025 template, then run a reviewed plan. This preflight never provisions resources.",
    }
    print(json.dumps(result, indent=2))
    return 0 if all(item["ok"] for item in required) else 2


if __name__ == "__main__":
    raise SystemExit(main())
