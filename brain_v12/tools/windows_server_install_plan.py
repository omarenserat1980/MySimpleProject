#!/usr/bin/env python3
"""Plan a safe Windows Server 2025 VM installation; never modifies disks or downloads media."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

SCHEMA = "brain.windows-server-install-plan.v1"
MIN_DISK_GIB = 64
GIB = 1024 ** 3
OFFICIAL_HOST_SUFFIXES = (".microsoft.com",)


def _sha256(value: str | None) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdefABCDEF" for c in value)


def verify_media_provenance(source_url: str, actual_sha256: str | None, trusted_sha256: str | None) -> dict:
    parsed = urlparse(source_url)
    host = (parsed.hostname or "").lower()
    official_source = parsed.scheme == "https" and any(
        host == suffix[1:] or host.endswith(suffix) for suffix in OFFICIAL_HOST_SUFFIXES
    )
    hash_format_ok = _sha256(actual_sha256) and _sha256(trusted_sha256)
    hash_match = bool(hash_format_ok and actual_sha256.lower() == trusted_sha256.lower())
    passed = official_source and hash_match
    return {
        "passed": passed,
        "source_url": source_url if official_source else None,
        "official_source_host": official_source,
        "trusted_checksum_supplied": _sha256(trusted_sha256),
        "sha256_match": hash_match,
        "reason": None if passed else "Require HTTPS Microsoft source URL and a matching trusted Microsoft checksum.",
        "note": "A locally computed hash without a trusted independent checksum does not prove authenticity.",
    }


def build_plan(*, source_url: str, actual_sha256: str | None, trusted_sha256: str | None,
               iso_size_bytes: int, disk_size_gib: int, backend: str,
               backend_available: bool, target_is_virtual_disk: bool,
               target_unambiguous: bool, destructive_authorized: bool) -> dict:
    media = verify_media_provenance(source_url, actual_sha256, trusted_sha256)
    disk_valid = isinstance(disk_size_gib, int) and disk_size_gib >= MIN_DISK_GIB
    backend_valid = backend in {"qemu-kvm", "hyper-v"} and backend_available
    safe_target = target_is_virtual_disk and target_unambiguous
    authorized = destructive_authorized
    checks = {
        "official_media": media,
        "iso_size": {"passed": isinstance(iso_size_bytes, int) and iso_size_bytes > 0, "size_bytes": iso_size_bytes},
        "virtual_disk_capacity": {"passed": disk_valid, "disk_size_gib": disk_size_gib, "minimum_gib": MIN_DISK_GIB},
        "execution_backend": {"passed": backend_valid, "backend": backend, "available": backend_available},
        "target_disk": {"passed": safe_target, "virtual_disk_only": target_is_virtual_disk, "unambiguous": target_unambiguous},
        "destructive_authorization": {"passed": authorized},
    }
    blockers = [name for name, result in checks.items() if not result.get("passed", False)]
    if blockers:
        status = "BLOCKED"
    else:
        status = "INSTALLATION_PLAN_READY"
    partitions = []
    if disk_valid:
        # Planning only: actual sizes are to be created by Windows Setup/DiskPart after
        # separate host and target identity checks. Do not issue disk operations here.
        partitions = [
            {"name": "EFI System", "size_mib": 260, "filesystem": "FAT32", "type": "EFI"},
            {"name": "Microsoft Reserved", "size_mib": 16, "filesystem": None, "type": "MSR"},
            {"name": "Windows", "size_mib": disk_size_gib * 1024 - 260 - 16 - 1024,
             "filesystem": "NTFS", "type": "OS"},
            {"name": "Windows Recovery", "size_mib": 1024, "filesystem": "NTFS", "type": "Recovery"},
        ]
    return {
        "schema": SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "boot_status": "NOT_TESTED",
        "source_media": {**media, "sha256": actual_sha256.lower() if _sha256(actual_sha256) else None,
                         "size_bytes": iso_size_bytes},
        "execution": {"backend": backend, "available": backend_available},
        "target": {"type": "virtual" if target_is_virtual_disk else "unknown_or_physical",
                   "unambiguous": target_unambiguous, "disk_size_gib": disk_size_gib},
        "partition_plan": {"scheme": "GPT", "firmware": "UEFI", "partitions": partitions,
                           "executed": False},
        "checks": checks,
        "blockers": blockers,
        "limitations": [
            "This command creates a plan only; it does not download media, create or format disks, start a VM, or install Windows.",
            "INSTALLATION_PLAN_READY is not installation or boot evidence.",
            "WINDOWS_FIRST_BOOT_VERIFIED requires independent guest-generated evidence from a real boot.",
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--iso-sha256", required=True)
    parser.add_argument("--trusted-sha256", required=True)
    parser.add_argument("--iso-size-bytes", required=True, type=int)
    parser.add_argument("--disk-size-gib", required=True, type=int)
    parser.add_argument("--backend", choices=("qemu-kvm", "hyper-v"), required=True)
    parser.add_argument("--backend-available", action="store_true")
    parser.add_argument("--target-is-virtual-disk", action="store_true")
    parser.add_argument("--target-unambiguous", action="store_true")
    parser.add_argument("--authorize-destructive-operations", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("windows-server-install-plan.json"))
    args = parser.parse_args(argv)
    report = build_plan(
        source_url=args.source_url, actual_sha256=args.iso_sha256, trusted_sha256=args.trusted_sha256,
        iso_size_bytes=args.iso_size_bytes, disk_size_gib=args.disk_size_gib, backend=args.backend,
        backend_available=args.backend_available, target_is_virtual_disk=args.target_is_virtual_disk,
        target_unambiguous=args.target_unambiguous,
        destructive_authorized=args.authorize_destructive_operations,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "boot_status": report["boot_status"],
                      "manifest": str(args.output), "blockers": report["blockers"]}, sort_keys=True))
    return 0 if report["status"] == "INSTALLATION_PLAN_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
