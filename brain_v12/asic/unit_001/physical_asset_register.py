#!/usr/bin/env python3
"""Fail-closed evidence register for physical BRAIN-ASIC-001 components.

This tool never discovers physical items by itself. A human must add evidence
after actual receipt/inspection. Simulation records cannot become inventory.
Uses only the Python standard library.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DEFAULT_REGISTER = ROOT / "physical_asset_register.json"


def validate_register(data: Any) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return {"valid": False, "errors": ["register must be a JSON object"], "physical_inventory_count_verified": 0, "market_value_total": None}
    if data.get("budget_jod") != 0:
        errors.append("budget_jod must remain 0 unless owner explicitly changes authorization")
    items = data.get("items")
    if not isinstance(items, list):
        errors.append("items must be a list")
        items = []
    seen: set[str] = set()
    verified = 0
    for i, item in enumerate(items):
        prefix = f"items[{i}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        asset_id = item.get("internal_asset_id")
        if not isinstance(asset_id, str) or not asset_id.strip():
            errors.append(f"{prefix} missing internal_asset_id")
        elif asset_id in seen:
            errors.append(f"duplicate internal_asset_id: {asset_id}")
        else:
            seen.add(asset_id)
        if item.get("evidence_class") == "PHYSICAL_OBSERVED":
            evidence = item.get("evidence", {})
            if not isinstance(evidence, dict) or not evidence.get("received_date") or not evidence.get("photo_urls"):
                errors.append(f"{asset_id or prefix}: PHYSICAL_OBSERVED requires received_date and photo_urls")
            else:
                verified += 1
        elif item.get("evidence_class") in ("SIMULATED", "DIGITAL_DESIGN", "ESTIMATED"):
            if item.get("counts_as_physical_inventory") is True:
                errors.append(f"{asset_id or prefix}: non-physical evidence cannot count as physical inventory")
        elif item.get("evidence_class") not in ("NOT_RECEIVED", "PHYSICAL_OBSERVED", "PHYSICAL_TESTED", "SOLD_AND_PAID", "SIMULATED", "DIGITAL_DESIGN", "ESTIMATED"):
            errors.append(f"{asset_id or prefix}: unknown evidence_class")
        valuation = item.get("market_valuation")
        if valuation is not None:
            if not isinstance(valuation, dict):
                errors.append(f"{asset_id or prefix}: market_valuation must be an object or null")
            else:
                if item.get("evidence_class") not in ("PHYSICAL_OBSERVED", "PHYSICAL_TESTED", "SOLD_AND_PAID"):
                    errors.append(f"{asset_id or prefix}: simulated/unreceived assets cannot have physical market valuation")
                for key in ("amount", "currency", "valuation_date", "source_urls", "condition"):
                    if not valuation.get(key):
                        errors.append(f"{asset_id or prefix}: market_valuation missing {key}")
        if item.get("sale_price_realized") is not None and item.get("evidence_class") != "SOLD_AND_PAID":
            errors.append(f"{asset_id or prefix}: realized sale requires SOLD_AND_PAID evidence")
        if item.get("revenue_received") is not None and not item.get("payment_evidence"):
            errors.append(f"{asset_id or prefix}: revenue_received requires payment_evidence")
    return {
        "valid": not errors,
        "errors": errors,
        "budget_jod": data.get("budget_jod"),
        "physical_inventory_count_verified": verified,
        "market_value_total": None,
        "market_value_note_ar": "لا يُحسب الإجمالي تلقائيًا قبل توحيد العملة والتحقق من مصادر تقييم كل أصل.",
        "realized_revenue": "NOT_VERIFIED",
        "financial_execution_enabled": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate BRAIN-ASIC-001 physical asset evidence")
    parser.add_argument("--register", type=Path, default=DEFAULT_REGISTER)
    parser.add_argument("--output", type=Path, help="Optional path to write JSON report")
    args = parser.parse_args()
    try:
        data = json.loads(args.register.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        report = {"valid": False, "errors": [f"cannot read register: {exc}"], "physical_inventory_count_verified": 0}
        code = 2
    else:
        report = validate_register(data)
        code = 0 if report["valid"] else 1
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
