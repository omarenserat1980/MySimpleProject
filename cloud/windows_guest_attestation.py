"""Attestation helpers for BRAIN Cloud Windows nodes.

This is an identity-binding layer, not a cryptographic proof of Azure hardware.
It binds a Fabric enrollment to stable guest identity evidence and records the
observation so the control plane can reject silent identity drift.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
from typing import Any


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def windows_guest_attestation() -> dict[str, Any]:
    if os.name != "nt":
        return {"platform": platform.system(), "verified_os": False}

    product = ""
    build = ""
    machine_guid = ""
    try:
        output = subprocess.check_output(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
             "(Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion').ProductName; "
             "(Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion').CurrentBuild; "
             "(Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion').UBR; "
             "(Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Cryptography').MachineGuid"],
            text=True, timeout=10,
        )
        lines = [x.strip() for x in output.splitlines() if x.strip()]
        if len(lines) >= 4:
            product, build, ubr, machine_guid = lines[:4]
        else:
            ubr = ""
    except Exception:
        ubr = ""

    verified_os = product.startswith("Windows Server 2025")
    identity_material = "|".join([product, build, ubr, machine_guid])
    return {
        "platform": "Windows",
        "product_name": product,
        "build": build,
        "verified_os": verified_os,
        "architecture": "x86_64" if platform.machine().lower() in {"amd64", "x86_64"} else platform.machine(),
        "guest_identity": _sha(identity_material) if identity_material else "",
        "evidence_type": "WINDOWS_GUEST_ATTESTATION",
    }


def validate_attestation(attestation: dict[str, Any]) -> tuple[bool, str]:
    if not isinstance(attestation, dict):
        return False, "ATTESTATION_INVALID"
    if not attestation.get("verified_os"):
        return False, "WINDOWS_SERVER_2025_NOT_VERIFIED"
    if attestation.get("architecture") not in {"x86_64", "amd64"}:
        return False, "WINDOWS_ARCHITECTURE_NOT_VERIFIED"
    if not attestation.get("guest_identity"):
        return False, "GUEST_IDENTITY_MISSING"
    return True, "OK"
