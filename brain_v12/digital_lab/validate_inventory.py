"""Validate Brain Digital Lab inventory reports without probing assets.

This checks report structure and evidence-state consistency only. It does not
validate runtime health or treat discovery metadata as proof of operation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REQUIRED_TOP_LEVEL = {
    "schema_version", "inventory_type", "generated_utc", "repository_root",
    "commit_sha", "asset_count", "coverage_limitations", "assets",
}
REQUIRED_ASSET_FIELDS = {
    "asset_id", "path", "domain", "size_bytes", "modified_utc",
    "lifecycle_status", "verification_status", "evidence",
}
REQUIRED_EVIDENCE_FIELDS = {"source", "tool_version", "source_revision", "reference", "observed_utc", "result", "check_id", "exit_status", "scope", "limitations"}
ARTIFACT_EVIDENCE_FIELDS = {"artifact_path", "artifact_size_bytes", "artifact_sha256"}
EVIDENCE_RESULTS = {"PASS", "FAIL", "BLOCKED", "NOT_RUN"}
LIFECYCLE_STATES = {"DISCOVERED_NOT_TESTED", "IN_REVIEW", "TESTING", "ACCEPTED", "REJECTED", "BLOCKED", "QUARANTINED"}
VERIFICATION_STATES = {"NOT_RUN", "PASS", "FAIL", "BLOCKED", "NOT_APPLICABLE"}


def validate_inventory(report: Any) -> list[str]:
    """Return validation errors; an empty list means structurally valid only."""
    errors: list[str] = []
    if not isinstance(report, dict):
        return ["report must be a JSON object"]
    missing = sorted(REQUIRED_TOP_LEVEL - report.keys())
    if missing:
        return [f"missing top-level fields: {', '.join(missing)}"]
    if report["schema_version"] != 1:
        errors.append("unsupported schema_version; expected 1")
    if report["inventory_type"] != "repository_path_metadata_only":
        errors.append("inventory_type must be repository_path_metadata_only")
    assets = report["assets"]
    if not isinstance(assets, list):
        return errors + ["assets must be a list"]
    if not isinstance(report["asset_count"], int) or isinstance(report["asset_count"], bool) or report["asset_count"] != len(assets):
        errors.append("asset_count must be an integer matching the assets list length")
    limitations = report["coverage_limitations"]
    if not isinstance(limitations, list) or not limitations or any(not isinstance(item, str) or not item.strip() for item in limitations):
        errors.append("coverage_limitations must be a non-empty list of non-empty strings")
    seen: set[str] = set()
    for index, asset in enumerate(assets):
        prefix = f"assets[{index}]"
        if not isinstance(asset, dict):
            errors.append(f"{prefix} must be an object")
            continue
        absent = sorted(REQUIRED_ASSET_FIELDS - asset.keys())
        if absent:
            errors.append(f"{prefix} missing fields: {', '.join(absent)}")
            continue
        path = asset["path"]
        if not isinstance(path, str) or not path or path.startswith("/") or "\\" in path:
            errors.append(f"{prefix}.path must be a non-empty repository-relative POSIX path")
        elif any(part in {"", ".", ".."} for part in path.split("/")):
            errors.append(f"{prefix}.path contains an unsafe path segment")
        if asset["asset_id"] != path:
            errors.append(f"{prefix}.asset_id must equal path")
        if isinstance(path, str):
            if path in seen:
                errors.append(f"duplicate asset path: {path}")
            seen.add(path)
        if not isinstance(asset["size_bytes"], int) or isinstance(asset["size_bytes"], bool) or asset["size_bytes"] < 0:
            errors.append(f"{prefix}.size_bytes must be a non-negative integer")
        lifecycle = asset["lifecycle_status"]
        verification = asset["verification_status"]
        if not isinstance(lifecycle, str) or lifecycle not in LIFECYCLE_STATES:
            errors.append(f"{prefix}.lifecycle_status is not recognized")
        if not isinstance(verification, str) or verification not in VERIFICATION_STATES:
            errors.append(f"{prefix}.verification_status is not recognized")
        evidence = asset["evidence"]
        if not isinstance(evidence, list):
            errors.append(f"{prefix}.evidence must be a list")
            evidence = []
        for evidence_index, item in enumerate(evidence):
            ep = f"{prefix}.evidence[{evidence_index}]"
            if not isinstance(item, dict):
                errors.append(f"{ep} must be an object")
                continue
            missing_evidence = sorted(REQUIRED_EVIDENCE_FIELDS - item.keys())
            if missing_evidence:
                errors.append(f"{ep} missing fields: {', '.join(missing_evidence)}")
                continue
            for field in REQUIRED_EVIDENCE_FIELDS - {"exit_status"}:
                if not isinstance(item[field], str) or not item[field].strip():
                    errors.append(f"{ep}.{field} must be a non-empty string")
            if not isinstance(item["result"], str) or item["result"] not in EVIDENCE_RESULTS:
                errors.append(f"{ep}.result must be one of {sorted(EVIDENCE_RESULTS)}")
            if not isinstance(item["exit_status"], int) or isinstance(item["exit_status"], bool):
                errors.append(f"{ep}.exit_status must be an integer")
            artifact_fields_present = ARTIFACT_EVIDENCE_FIELDS.intersection(item)
            if artifact_fields_present and artifact_fields_present != ARTIFACT_EVIDENCE_FIELDS:
                errors.append(f"{ep} must provide artifact_path, artifact_size_bytes, and artifact_sha256 together")
            if artifact_fields_present == ARTIFACT_EVIDENCE_FIELDS:
                if not isinstance(item["artifact_path"], str) or not item["artifact_path"].strip():
                    errors.append(f"{ep}.artifact_path must be a non-empty string")
                if not isinstance(item["artifact_size_bytes"], int) or isinstance(item["artifact_size_bytes"], bool) or item["artifact_size_bytes"] < 0:
                    errors.append(f"{ep}.artifact_size_bytes must be a non-negative integer")
                digest = item["artifact_sha256"]
                if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdefABCDEF" for c in digest):
                    errors.append(f"{ep}.artifact_sha256 must be a 64-character hexadecimal SHA-256")
        if lifecycle == "DISCOVERED_NOT_TESTED" and verification != "NOT_RUN":
            errors.append(f"{prefix} cannot claim verification before leaving DISCOVERED_NOT_TESTED")
        evidence_results = {
            item.get("result") for item in evidence
            if isinstance(item, dict) and isinstance(item.get("result"), str)
        }
        if verification in {"PASS", "FAIL", "BLOCKED"} and not evidence:
            errors.append(f"{prefix} cannot claim {verification} without evidence")
        if verification in {"PASS", "FAIL", "BLOCKED"} and verification not in evidence_results:
            errors.append(f"{prefix} verification status {verification} requires matching evidence result")
        if lifecycle == "ACCEPTED" and (verification != "PASS" or "PASS" not in evidence_results):
            errors.append(f"{prefix} cannot be ACCEPTED without PASS verification and matching evidence")
        if lifecycle == "REJECTED" and (verification != "FAIL" or "FAIL" not in evidence_results):
            errors.append(f"{prefix} cannot be REJECTED without FAIL verification and matching evidence")
        if lifecycle == "BLOCKED" and verification != "BLOCKED":
            errors.append(f"{prefix} cannot be BLOCKED without BLOCKED verification status")
        if verification == "BLOCKED" and lifecycle not in {"BLOCKED", "QUARANTINED"}:
            errors.append(f"{prefix} BLOCKED verification requires BLOCKED or QUARANTINED lifecycle")
        if not isinstance(asset["domain"], str) or not asset["domain"].strip():
            errors.append(f"{prefix}.domain must be a non-empty string")
        if not isinstance(asset["modified_utc"], str) or not asset["modified_utc"].strip():
            errors.append(f"{prefix}.modified_utc must be a non-empty string")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path, help="path to inventory JSON")
    args = parser.parse_args()
    try:
        report = json.loads(args.inventory.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "INVALID", "errors": [str(exc)]}, ensure_ascii=False))
        return 2
    errors = validate_inventory(report)
    print(json.dumps({"status": "VALID" if not errors else "INVALID",
                      "asset_count": report.get("asset_count") if isinstance(report, dict) else None,
                      "errors": errors}, ensure_ascii=False))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
