"""Fail-closed integrity checker for a Brain mining evidence bundle.

This verifies bundle structure and local SHA-256 integrity only. It does not
authenticate a device, contact a mining pool, or prove accepted shares/payout.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

REQUIRED_ARTIFACTS = (
    "host_attestation",
    "brain_connection",
    "pool_session",
    "accepted_shares",
    "payout",
    "wallet_transaction",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_bundle(manifest_path: str | Path) -> dict[str, Any]:
    """Check manifest shape, referenced files, digests, and evidence presence.

    'integrity_ok' means only that listed local files match their declared
    digest. It is never equivalent to independent evidence verification.
    """
    manifest_file = Path(manifest_path)
    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return _blocked("MANIFEST_UNREADABLE", REQUIRED_ARTIFACTS)

    if not isinstance(manifest, dict) or not isinstance(manifest.get("artifacts"), dict):
        return _blocked("INVALID_MANIFEST_SHAPE", REQUIRED_ARTIFACTS)

    artifacts = manifest["artifacts"]
    missing = [name for name in REQUIRED_ARTIFACTS if name not in artifacts]
    invalid: list[str] = []
    verified: list[str] = []

    for name, item in artifacts.items():
        if not isinstance(item, dict):
            invalid.append(name)
            continue
        relpath, expected = item.get("path"), item.get("sha256")
        if not isinstance(relpath, str) or not relpath or not isinstance(expected, str):
            invalid.append(name)
            continue
        # Keep referenced files within the manifest directory.
        base = manifest_file.resolve().parent
        target = (base / relpath).resolve()
        if target != base and base not in target.parents:
            invalid.append(name)
            continue
        if len(expected) != 64 or any(c not in "0123456789abcdefABCDEF" for c in expected):
            invalid.append(name)
            continue
        try:
            actual = sha256_file(target)
        except OSError:
            invalid.append(name)
            continue
        if actual.lower() != expected.lower():
            invalid.append(name)
        else:
            verified.append(name)

    integrity_ok = not invalid and not missing
    return {
        "state": "INTEGRITY_CHECK_PASSED_NOT_INDEPENDENTLY_VERIFIED" if integrity_ok else "BLOCKED",
        "integrity_ok": integrity_ok,
        "independently_verified": False,
        "real_mining_verified": False,
        "revenue_verified": False,
        "verified_file_digests": sorted(verified),
        "missing_artifacts": sorted(missing),
        "invalid_artifacts": sorted(set(invalid)),
        "limitations": [
            "File hashes prove local file integrity only, not source authenticity.",
            "Pool accepted shares require independent pool-side confirmation.",
            "Payout requires independent payment and wallet/on-chain verification.",
        ],
    }


def _blocked(reason: str, missing: tuple[str, ...]) -> dict[str, Any]:
    return {
        "state": "BLOCKED",
        "integrity_ok": False,
        "independently_verified": False,
        "real_mining_verified": False,
        "revenue_verified": False,
        "reason": reason,
        "verified_file_digests": [],
        "missing_artifacts": list(missing),
        "invalid_artifacts": [],
    }


def write_example_manifest(directory: str | Path) -> Path:
    """Create an explicitly synthetic example bundle for testing/documentation."""
    base = Path(directory)
    base.mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, dict[str, str]] = {}
    for name in REQUIRED_ARTIFACTS:
        target = base / f"EXAMPLE_ONLY_{name}.txt"
        target.write_text("SYNTHETIC EXAMPLE - NOT REAL MINING EVIDENCE\n", encoding="utf-8")
        artifacts[name] = {"path": target.name, "sha256": sha256_file(target)}
    manifest_path = base / "EXAMPLE_ONLY_manifest.json"
    manifest_path.write_text(json.dumps({"artifacts": artifacts}, indent=2) + "\n", encoding="utf-8")
    return manifest_path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", help="Path to an evidence bundle manifest JSON")
    args = parser.parse_args()
    print(json.dumps(verify_bundle(args.manifest), indent=2))
