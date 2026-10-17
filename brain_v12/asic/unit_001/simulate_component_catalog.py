"""Validate and report the Arabic BRAIN-ASIC-001 simulated component catalog.

This tool is for simulation and schema checks only. It cannot establish real
part identity, factory serial numbers, manufacturing, or assembly readiness.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
DEFAULT_CATALOG = HERE / "simulated_component_catalog.ar.json"


def validate_catalog(catalog: dict[str, Any]) -> dict[str, Any]:
    components = catalog.get("components", [])
    ids = [item.get("serial_simulation_id") for item in components]
    duplicate_ids = sorted({value for value in ids if value and ids.count(value) > 1})
    missing_ids = [item.get("ref", "UNKNOWN") for item in components
                   if not item.get("serial_simulation_id")]
    unsafe_records = [
        item.get("ref", "UNKNOWN")
        for item in components
        if item.get("evidence_class") != "SIMULATED"
        or item.get("physical_identity_verified") is not False
        or item.get("physical_manufacturing_verified") is not False
        or item.get("assembly_ready") is not False
    ]
    policy = catalog.get("simulation_policy", {})
    policy_ok = (
        policy.get("all_records_are_simulated") is True
        and policy.get("serial_numbers_are_internal_simulation_ids_not_factory_serials") is True
        and policy.get("candidate_part_numbers_are_not_approved_for_physical_assembly") is True
        and policy.get("do_not_use_simulated_electrical_values_for_power_on_or_pcb_fabrication") is True
    )
    errors = []
    if not components:
        errors.append("لا توجد قطع في الكتالوج")
    if duplicate_ids:
        errors.append("معرّفات محاكاة مكررة: " + ", ".join(duplicate_ids))
    if missing_ids:
        errors.append("معرّفات محاكاة ناقصة: " + ", ".join(missing_ids))
    if unsafe_records:
        errors.append("سجلات لا تحافظ على حدود المحاكاة: " + ", ".join(unsafe_records))
    if not policy_ok:
        errors.append("سياسة المحاكاة والسلامة ناقصة أو غير صحيحة")
    return {
        "schema": "brain-asic-simulation-validation/v1",
        "language": "ar",
        "product_id": catalog.get("product_id"),
        "catalog_revision": catalog.get("catalog_revision"),
        "evidence_class": "SIMULATED",
        "simulated": True,
        "validation_passed": not errors,
        "component_count": len(components),
        "unique_simulation_id_count": len({value for value in ids if value}),
        "duplicate_simulation_ids": duplicate_ids,
        "real_component_count_verified": 0,
        "physical_serial_numbers_verified": 0,
        "manufacturing_order_sent": False,
        "ready_for_assembly": False,
        "errors_ar": errors,
        "warning_ar": "نجاح هذا الفحص يثبت سلامة بنية بيانات المحاكاة فقط؛ لا يثبت مواصفات قطع حقيقية أو تصنيعًا أو جاهزية تجميع.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="فحص كتالوج قطع Brain المحاكى")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    report = validate_catalog(catalog)
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0 if report["validation_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
