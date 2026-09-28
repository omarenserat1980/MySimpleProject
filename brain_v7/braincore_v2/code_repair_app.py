"""Bounded code-repair application for Electronic Brain.

Pipeline:
  collect failure -> classify -> run allowlisted healer -> verify -> report.

The application never executes repair instructions taken from an error log and
never rewrites arbitrary source. Actual edits remain inside code_self_healer's
allowlist and deterministic rules.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .code_self_healer import MAX_CYCLES, diagnose_failure, heal


def classify(error_text: str) -> dict[str, Any]:
    diagnosis = diagnose_failure(error_text or "")
    return {
        "failure_class": diagnosis.get("class", "unknown"),
        "repair_rule": diagnosis.get("repair", "none_allowlisted"),
        "safe_to_auto_repair": diagnosis.get("repair", "none_allowlisted") != "none_allowlisted",
    }


def run_repair(
    error_text: str = "",
    *,
    report_path: str = "code_repair_report.json",
) -> dict[str, Any]:
    classification = classify(error_text)
    result = heal(error_text, report_path)
    report = {
        "application": "electronic_brain_code_repair",
        "version": 1,
        "classification": classification,
        "status": result.get("status"),
        "cycles_completed": result.get("cycles_completed", 0),
        "changed_files": result.get("changed_files", []),
        "history": result.get("history", []),
        "last_error": result.get("last_error", ""),
        "max_cycles": MAX_CYCLES,
        "safety": {
            "allowlisted_repairs_only": True,
            "rollback_on_failed_verification": True,
            "no_arbitrary_log_instructions": True,
        },
    }
    Path(report_path).write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Electronic Brain bounded code repair app")
    parser.add_argument("--error-file", default="")
    parser.add_argument("--report", default="code_repair_report.json")
    args = parser.parse_args()

    error_text = ""
    if args.error_file:
        error_text = Path(args.error_file).read_text(encoding="utf-8")[-12000:]

    report = run_repair(error_text, report_path=args.report)
    print(json.dumps({
        "status": report["status"],
        "failure_class": report["classification"]["failure_class"],
        "repair_rule": report["classification"]["repair_rule"],
        "cycles_completed": report["cycles_completed"],
        "changed_files": report["changed_files"],
    }, ensure_ascii=False))
    return 0 if report["status"] == "CODE_VERIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
