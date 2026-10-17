"""BRAIN-ASIC-001 component information tool.

Reports a component-by-component dossier and readiness blockers. It does not
invent part numbers or treat the BRAIN AI project label as proof of fabrication.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DEFAULT = PROJECT_ROOT / "artifacts" / "asic-unit-001" / "component-dossier.json"

COMPONENTS: list[dict[str, Any]] = [
    {"ref": "U1", "name": "SHA-256d compute device", "category": "compute",
     "purpose": "Hash block headers and search proof-of-work nonces",
     "required_fields": ["manufacturer", "exact_part_number", "package", "datasheet_url",
                         "pinout_source", "operating_rails", "max_ratings", "clock_reset",
                         "interface_protocol", "thermal_limits"],
     "part_number": None, "status": "BLOCKED_DEVICE_NOT_SELECTED"},
    {"ref": "U2", "name": "Host/controller", "category": "control",
     "purpose": "Load jobs, configure compute device, collect status/results",
     "required_fields": ["exact_part_number", "datasheet_url", "interface_compatibility",
                         "firmware_source", "logic_voltage", "debug_method"],
     "part_number": None, "status": "BLOCKED_DEPENDS_ON_U1"},
    {"ref": "U3", "name": "Core power regulator", "category": "power",
     "purpose": "Supply the compute core rail(s)",
     "required_fields": ["exact_part_number", "datasheet_url", "input_range_v",
                         "output_voltage_v", "continuous_current_a", "transient_response",
                         "thermal_derating", "power_sequence"],
     "part_number": None, "status": "BLOCKED_DEPENDS_ON_U1"},
    {"ref": "U4", "name": "I/O power regulator", "category": "power",
     "purpose": "Supply controller and device I/O rails",
     "required_fields": ["exact_part_number", "datasheet_url", "output_voltage_v",
                         "continuous_current_a", "logic_compatibility"],
     "part_number": None, "status": "BLOCKED_DEPENDS_ON_INTERFACE"},
    {"ref": "U5", "name": "Input protection", "category": "protection",
     "purpose": "Protect against documented input faults",
     "required_fields": ["exact_part_number", "datasheet_url", "input_voltage_range_v",
                         "current_rating_a", "reverse_polarity_strategy", "surge_rating"],
     "part_number": None, "status": "BLOCKED_DEPENDS_ON_POWER_BUDGET"},
    {"ref": "U6", "name": "Clock source", "category": "timing",
     "purpose": "Provide required reference clock where the chosen device needs one",
     "required_fields": ["exact_part_number", "datasheet_url", "frequency_hz",
                         "tolerance_ppm", "output_standard", "load_requirements"],
     "part_number": None, "status": "BLOCKED_DEPENDS_ON_U1"},
    {"ref": "U7", "name": "Reset/configuration interface", "category": "control",
     "purpose": "Safe startup, reset and programming/debug",
     "required_fields": ["exact_part_number", "datasheet_url", "reset_polarity",
                         "startup_timing", "programming_interface"],
     "part_number": None, "status": "BLOCKED_DEPENDS_ON_U1"},
    {"ref": "U8", "name": "Thermal sensor", "category": "thermal",
     "purpose": "Observe board/device temperature if required by hardware safety design",
     "required_fields": ["exact_part_number", "datasheet_url", "measurement_range_c",
                         "accuracy_c", "interface", "placement_rule", "fault_response"],
     "part_number": None, "status": "BLOCKED_SENSOR_NOT_SELECTED"},
    {"ref": "U9", "name": "Fan driver / fan", "category": "thermal",
     "purpose": "Remove heat based on verified dissipation and thermal design",
     "required_fields": ["exact_part_number", "datasheet_url", "rated_voltage_v",
                         "current_a", "airflow_or_thermal_data", "control_interface"],
     "part_number": None, "status": "BLOCKED_THERMAL_BUDGET"},
    {"ref": "J1", "name": "Power connector", "category": "connector",
     "purpose": "Bring power safely to the board",
     "required_fields": ["exact_part_number", "datasheet_url", "pinout", "current_rating_a",
                         "wire_gauge", "mating_part", "footprint_source"],
     "part_number": None, "status": "BLOCKED_DEPENDS_ON_POWER_BUDGET"},
    {"ref": "J2", "name": "Host/data connector", "category": "connector",
     "purpose": "Connect host/controller and data interface",
     "required_fields": ["exact_part_number", "datasheet_url", "pinout", "protocol",
                         "voltage_levels", "footprint_source"],
     "part_number": None, "status": "BLOCKED_DEPENDS_ON_INTERFACE"},
    {"ref": "R/C/L", "name": "Passive components", "category": "passives",
     "purpose": "Decoupling, feedback, filtering, pull-ups and signal conditioning",
     "required_fields": ["exact_part_number", "value", "tolerance", "voltage_or_power_rating",
                         "package", "datasheet_url", "design_calculation"],
     "part_number": None, "status": "BLOCKED_UNTIL_SCHEMATIC"},
    {"ref": "HS1", "name": "Heatsink / thermal interface", "category": "thermal",
     "purpose": "Transfer device heat to ambient",
     "required_fields": ["exact_part_number", "datasheet_url", "thermal_resistance_c_per_w",
                         "mechanical_fit", "interface_material", "airflow_assumption"],
     "part_number": None, "status": "BLOCKED_UNTIL_POWER_AND_PACKAGE_KNOWN"},
    {"ref": "PCB1", "name": "Printed circuit board", "category": "pcb",
     "purpose": "Interconnect all selected components",
     "required_fields": ["revision", "native_cad_path", "stackup", "copper_weight",
                         "minimum_trace_clearance", "erc_report", "drc_report",
                         "fabrication_outputs_reviewed"],
     "part_number": None, "status": "NOT_DESIGNED"},
]

def build_dossier() -> dict[str, Any]:
    parts = []
    for component in COMPONENTS:
        parts.append({
            **component,
            "manufacturer_label": "BRAIN AI (project designation)",
            "physical_manufacturing_verified": False,
            "identity_fields_complete": False,
            "missing_fields": list(component["required_fields"]),
            "evidence_class": "DESIGN_REGISTER",
        })
    return {
        "schema": "brain-asic-component-dossier/v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "product_id": "BRAIN-ASIC-001",
        "project_manufacturer_label": "BRAIN AI",
        "legal_company_registration_verified": False,
        "physical_manufacturing_verified": False,
        "budget_jod": 0,
        "purchases_authorized": False,
        "evidence_class": "DESIGN_REGISTER",
        "simulated": False,
        "status": "BLOCKED_PART_IDENTIFICATION",
        "component_count": len(parts),
        "identified_exact_part_count": sum(bool(p["part_number"]) for p in parts),
        "ready_for_assembly": False,
        "components": parts,
        "blockers": [
            "Select the compute-device path and exact device/board part number.",
            "Obtain authoritative datasheet and verified package/pinout.",
            "Calculate power rails and thermal budget from the exact device.",
            "Complete schematic, BOM, footprint verification, ERC and PCB DRC.",
            "Do not interpret the BRAIN AI project manufacturer label as proof of physical fabrication.",
        ],
    }

def main() -> int:
    parser = argparse.ArgumentParser(description="Generate BRAIN-ASIC-001 component dossier")
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT)
    parser.add_argument("--stdout", action="store_true", help="print JSON instead of writing a file")
    args = parser.parse_args()
    report = build_dossier()
    serialized = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.stdout:
        print(serialized, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
        print(f"wrote {args.output}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
