#!/usr/bin/env python3
"""Audit ASIC lifecycle evidence without inferring physical fabrication from simulation.

The gate is deliberately fail-closed: a stage passes only when its required artifacts
exist, are non-empty, match their declared SHA-256 hashes, and have the required
metadata. This verifies evidence packaging, not the truth of an external claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

STAGES = [
    ("rtl_simulation", ["test_log"]),
    ("synthesis", ["netlist", "synthesis_log"]),
    ("physical_design", ["layout", "drc_report", "lvs_report"]),
    ("tapeout", ["tapeout_receipt"]),
    ("foundry_fabrication", ["foundry_receipt", "lot_or_wafer_id"]),
    ("silicon_test", ["test_report", "raw_measurements", "device_or_die_id"]),
]
LAYOUT_SUFFIXES = {".gds", ".gdsii", ".oas", ".oasis"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def audit(manifest_path: Path) -> dict[str, Any]:
    root = manifest_path.resolve().parent
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"schema_version": 1, "overall_status": "INVALID_MANIFEST",
                "fabrication_claim_allowed": False, "errors": [str(exc)], "stages": {}}

    artifacts = manifest.get("artifacts", {})
    stages_out: dict[str, Any] = {}
    for stage, required in STAGES:
        declared = manifest.get("stages", {}).get(stage, {})
        checks: list[dict[str, Any]] = []
        for key in required:
            item = artifacts.get(declared.get(key, ""))
            if not isinstance(item, dict):
                checks.append({"item": key, "ok": False, "reason": "artifact_not_declared"})
                continue
            rel = item.get("path")
            expected = str(item.get("sha256", "")).lower()
            if not rel:
                checks.append({"item": key, "ok": False, "reason": "path_missing"})
                continue
            path = (root / rel).resolve()
            if root not in path.parents and path != root:
                checks.append({"item": key, "ok": False, "reason": "path_outside_evidence_root"})
                continue
            if not path.is_file() or path.stat().st_size == 0:
                checks.append({"item": key, "ok": False, "reason": "file_missing_or_empty", "path": rel})
                continue
            actual = sha256_file(path)
            if len(expected) != 64 or actual != expected:
                checks.append({"item": key, "ok": False, "reason": "sha256_missing_or_mismatch",
                               "path": rel, "actual_sha256": actual})
                continue
            checks.append({"item": key, "ok": True, "path": rel, "sha256": actual,
                           "bytes": path.stat().st_size})
            if key == "layout" and path.suffix.lower() not in LAYOUT_SUFFIXES:
                checks[-1].update(ok=False, reason="layout_must_be_GDSII_or_OASIS")
            if key in {"tapeout_receipt", "foundry_receipt"}:
                if not item.get("issuer") or not item.get("issued_at") or not item.get("external_reference"):
                    checks[-1].update(ok=False, reason="external_receipt_metadata_missing")
        passed = bool(checks) and all(c["ok"] for c in checks)
        stages_out[stage] = {"status": "PASS" if passed else "BLOCKED", "checks": checks}

    # A status label or user-supplied boolean is never accepted as physical proof.
    physical_complete = all(stages_out[s]["status"] == "PASS"
                            for s, _ in STAGES[2:])
    rtl_only = stages_out["rtl_simulation"]["status"] == "PASS" and not physical_complete
    overall = "SILICON_EVIDENCE_COMPLETE" if physical_complete else (
        "RTL_SIMULATION_ONLY" if rtl_only else "EVIDENCE_INCOMPLETE")
    return {
        "schema_version": 1,
        "project": manifest.get("project", "unspecified"),
        "manifest_sha256": sha256_file(manifest_path),
        "overall_status": overall,
        "fabrication_claim_allowed": physical_complete,
        "important_limit": "This tool checks files, hashes and metadata only; external claims require independent verification.",
        "stages": stages_out,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="JSON evidence manifest")
    parser.add_argument("--output", type=Path, help="write audit JSON to this path")
    args = parser.parse_args()
    result = audit(args.manifest)
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if result.get("overall_status") in {"RTL_SIMULATION_ONLY", "SILICON_EVIDENCE_COMPLETE"} else 2


if __name__ == "__main__":
    sys.exit(main())
