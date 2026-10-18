#!/usr/bin/env python3
"""Diagnose Brain ASIC cloud-build rejection causes from CI evidence logs."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REQUIRED_MARKERS = {
    "sha256-vector.log": ["BRAIN_SHA256_COMPRESS_VECTOR=PASS"],
    "sha256d-vector.log": ["BRAIN_SHA256D_GENESIS=PASS"],
    "nonce-search.log": [
        "BRAIN_NONCE_TARGET_REJECT=PASS",
        "BRAIN_NONCE_SEARCH_GENESIS=PASS",
    ],
    "smoke.log": ["BRAIN_ASIC_V1_SMOKE=PASS"],
}
FATAL_PATTERNS = [
    re.compile(r"\bERROR\s*:", re.IGNORECASE),
    re.compile(r"\bFATAL\s*:", re.IGNORECASE),
    re.compile(r"Traceback \(most recent call last\)", re.IGNORECASE),
    re.compile(r"\bBRAIN_[A-Z0-9_]+=FAIL\b"),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    findings: list[dict[str, str]] = []
    missing: list[dict[str, str]] = []
    checked_logs = 0

    for filename, markers in REQUIRED_MARKERS.items():
        path = args.build_dir / filename
        if not path.is_file():
            missing.append({"file": filename, "reason": "required evidence log missing"})
            continue
        checked_logs += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        for marker in markers:
            if marker not in text:
                missing.append({"file": filename, "reason": f"required PASS marker missing: {marker}"})

    for path in sorted(args.build_dir.glob("*.log")):
        checked_logs += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), start=1):
            for pattern in FATAL_PATTERNS:
                if pattern.search(line):
                    findings.append({
                        "file": path.name,
                        "line": str(line_no),
                        "reason": line.strip()[:500],
                    })
                    break

    expected_json = [
        "brain_sha256_compress.json",
        "brain_sha256d_header.json",
        "brain_sha256_core.json",
    ]
    for filename in expected_json:
        if not (args.build_dir / filename).is_file():
            missing.append({"file": filename, "reason": "expected Yosys netlist JSON missing"})

    status = "PASS" if not findings and not missing else "REJECT"
    report = {
        "schema": "brain-asic-rejection-diagnostics/v1",
        "status": status,
        "checked_log_count": checked_logs,
        "findings": findings,
        "missing_evidence": missing,
        "limitations": [
            "CI simulation and Yosys synthesis evidence only; not proof of fabricated ASIC hardware.",
            "A PASS does not establish real Bitcoin mining, pool acceptance, or revenue.",
        ],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
