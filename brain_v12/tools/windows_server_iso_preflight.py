#!/usr/bin/env python3
"""Read-only Windows Server ISO structural preflight; never claims guest boot."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REQUIRED_FILES = (
    "efi/boot/bootx64.efi",
    "sources/boot.wim",
)
INSTALL_IMAGES = ("sources/install.wim", "sources/install.esd")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_iso(iso: Path) -> dict:
    report = {
        "schema": "brain.windows-iso-preflight.v1",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "iso_name": iso.name,
        "status": "NOT_TESTED",
        "boot_status": "NOT_TESTED",
        "checks": {},
        "limitations": [
            "Structural validation is not firmware boot evidence.",
            "No Windows Setup or installed operating system was executed.",
            "This tool does not modify or rebuild the source ISO.",
        ],
    }
    if not iso.is_file() or iso.stat().st_size == 0:
        report["status"] = "BLOCKED"
        report["checks"]["iso_file"] = {"passed": False, "reason": "ISO missing or empty"}
        return report

    report["checks"]["iso_file"] = {"passed": True, "size_bytes": iso.stat().st_size}
    report["sha256"] = sha256_file(iso)
    xorriso = shutil.which("xorriso")
    if not xorriso:
        report["status"] = "BLOCKED"
        report["checks"]["xorriso"] = {"passed": False, "reason": "xorriso not installed"}
        return report

    try:
        version = subprocess.run(
            [xorriso, "-version"], capture_output=True, text=True, timeout=15, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        report["status"] = "BLOCKED"
        report["checks"]["xorriso"] = {
            "passed": False,
            "reason": f"xorriso version probe failed: {type(exc).__name__}",
        }
        return report
    report["tool"] = {"name": "xorriso", "version": (version.stdout or version.stderr).splitlines()[:2]}
    try:
        listing = subprocess.run(
            [xorriso, "-indev", str(iso), "-find", "/", "-type", "f", "-print"],
            capture_output=True, text=True, timeout=120, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        report["status"] = "BLOCKED"
        report["checks"]["iso9660_listing"] = {
            "passed": False,
            "reason": f"xorriso ISO listing failed: {type(exc).__name__}",
        }
        return report
    report["checks"]["iso9660_listing"] = {
        "passed": listing.returncode == 0,
        "returncode": listing.returncode,
    }
    if listing.returncode != 0:
        report["checks"]["iso9660_listing"]["reason"] = "xorriso could not enumerate ISO contents"
        report["status"] = "BLOCKED"
        return report

    paths = set()
    for line in listing.stdout.splitlines():
        line = line.strip()
        # xorriso may print status lines; only normalize path-like lines.
        if line.startswith("/"):
            paths.add(line.lstrip("/").replace("\\", "/").casefold())
    required_missing = [name for name in REQUIRED_FILES if name not in paths]
    install_found = [name for name in INSTALL_IMAGES if name in paths]
    report["checks"]["uefi_and_setup_files"] = {
        "passed": not required_missing and bool(install_found),
        "required_files_missing": required_missing,
        "install_image_found": install_found,
    }
    report["status"] = (
        "ISO_STRUCTURE_VALIDATED"
        if not required_missing and install_found
        else "BLOCKED"
    )
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iso", required=True, type=Path, help="Read-only source ISO")
    parser.add_argument("--output", type=Path, default=Path("windows-iso-preflight.json"))
    args = parser.parse_args(argv)
    report = inspect_iso(args.iso)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "boot_status": report["boot_status"],
                      "manifest": str(args.output), "sha256": report.get("sha256")}, sort_keys=True))
    return 0 if report["status"] == "ISO_STRUCTURE_VALIDATED" else 2


if __name__ == "__main__":
    sys.exit(main())
