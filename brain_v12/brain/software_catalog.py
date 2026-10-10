"""Declarative software catalog for Brain's staged runtime roadmap.

This catalog describes intended roles and verification gates. It is not evidence that
software is installed, licensed, available, or executable on any host.
"""
from __future__ import annotations

from typing import Any

CATALOG_VERSION = 1

DEFAULT_SOFTWARE_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "software_id": "brain-v12",
        "name": "Electronic Brain V12",
        "category": "application",
        "target_state": "running",
        "priority": "critical",
        "execution_class": "application",
        "required_for": ["brain-api", "software-management"],
        "source_policy": "owned-repository",
        "license_policy": "verify-repository-license",
        "install_allowed": False,
        "verification_gates": ["source-revision", "unit-tests", "health-check"],
    },
    {
        "software_id": "python-runtime",
        "name": "Python",
        "category": "runtime",
        "target_state": "installed",
        "priority": "critical",
        "execution_class": "runtime",
        "required_for": ["brain-api", "automation"],
        "source_policy": "approved-package-source",
        "license_policy": "PSF-license-review",
        "install_allowed": False,
        "verification_gates": ["version", "path", "runtime-smoke-test"],
    },
    {
        "software_id": "sqlite",
        "name": "SQLite",
        "category": "database",
        "target_state": "installed",
        "priority": "high",
        "execution_class": "data-store",
        "required_for": ["software-registry", "local-memory"],
        "source_policy": "approved-runtime-distribution",
        "license_policy": "public-domain-license-review",
        "install_allowed": False,
        "verification_gates": ["library-version", "read-write-round-trip", "backup-restore"],
    },
    {
        "software_id": "git",
        "name": "Git",
        "category": "developer-tool",
        "target_state": "installed",
        "priority": "high",
        "execution_class": "source-control",
        "required_for": ["source-audit", "change-review"],
        "source_policy": "approved-package-source",
        "license_policy": "GPL-license-review",
        "install_allowed": False,
        "verification_gates": ["version", "repository-read-only-check"],
    },
    {
        "software_id": "dotnet-sdk",
        "name": ".NET SDK",
        "category": "developer-tool",
        "target_state": "planned",
        "priority": "medium",
        "execution_class": "compiler",
        "required_for": ["future-dotnet-projects"],
        "source_policy": "official-vendor-source",
        "license_policy": "vendor-terms-review",
        "install_allowed": False,
        "verification_gates": ["version", "sdk-list", "sample-build"],
    },
    {
        "software_id": "windows-server-2025",
        "name": "Windows Server 2025",
        "category": "operating-system",
        "target_state": "planned",
        "priority": "critical",
        "execution_class": "virtual-machine",
        "required_for": ["windows-cloud-executor"],
        "source_policy": "Azure-approved-image",
        "license_policy": "Azure-image-license-and-cost-review",
        "install_allowed": False,
        "verification_gates": ["azure-resource-readback", "vm-power-state", "guest-boot-proof", "remote-access-hardening"],
    },
    {
        "software_id": "qemu",
        "name": "QEMU",
        "category": "virtualization",
        "target_state": "planned",
        "priority": "high",
        "execution_class": "virtual-machine-monitor",
        "required_for": ["real-windows-boot-evidence"],
        "source_policy": "approved-package-source",
        "license_policy": "GPL-license-review",
        "install_allowed": False,
        "verification_gates": ["version", "kvm-capability", "isolated-boot-test"],
    },
    {
        "software_id": "ovmf",
        "name": "OVMF UEFI firmware",
        "category": "virtualization",
        "target_state": "planned",
        "priority": "high",
        "execution_class": "firmware",
        "required_for": ["uefi-virtual-machine-boot"],
        "source_policy": "approved-package-source",
        "license_policy": "firmware-license-review",
        "install_allowed": False,
        "verification_gates": ["firmware-file-present", "hash-or-package-proof", "boot-test"],
    },
    {
        "software_id": "ffmpeg",
        "name": "FFmpeg / FFprobe",
        "category": "media-tool",
        "target_state": "planned",
        "priority": "low",
        "execution_class": "media-processing",
        "required_for": ["video-production"],
        "source_policy": "approved-package-source",
        "license_policy": "build-configuration-and-codec-license-review",
        "install_allowed": False,
        "verification_gates": ["version", "codec-inventory", "sample-transcode"],
    },
)


def get_catalog() -> dict[str, Any]:
    """Return a defensive copy of the desired catalog."""
    return {
        "ok": True,
        "catalog_version": CATALOG_VERSION,
        "execution_enabled": False,
        "items": [dict(item, required_for=list(item["required_for"]),
                       verification_gates=list(item["verification_gates"]))
                  for item in DEFAULT_SOFTWARE_CATALOG],
        "note": "Desired-state catalog only; it is not a live host inventory."
    }


def build_readiness(registry_items: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare catalog targets with registry records without running host probes."""
    observed = {item.get("software_id"): item for item in registry_items}
    rows = []
    for target in DEFAULT_SOFTWARE_CATALOG:
        record = observed.get(target["software_id"])
        rows.append({
            "software_id": target["software_id"],
            "name": target["name"],
            "priority": target["priority"],
            "target_state": target["target_state"],
            "inventory_state": record.get("runtime_state", "not-registered") if record else "not-registered",
            "verification_state": record.get("verification_state", "unverified") if record else "unverified",
            "ready": bool(record and record.get("verification_state") == "verified"
                          and record.get("runtime_state") == target["target_state"]),
            "install_allowed": False,
        })
    return {
        "ok": True,
        "catalog_version": CATALOG_VERSION,
        "items": rows,
        "ready_count": sum(1 for row in rows if row["ready"]),
        "total": len(rows),
        "execution_enabled": False,
    }
