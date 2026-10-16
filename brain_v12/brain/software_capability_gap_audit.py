"""Evidence-aware capability gap audit for Electronic Brain.

This module consumes the read-only software inventory and produces a plan.
It deliberately does not register detected components as online executors,
contact remote devices, generate executable code, or enable mining.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from brain_v12.brain.software_node_discovery import discover

ROOT = Path(__file__).resolve().parents[2]

# Capability requirements are explicit and conservative. Presence alone is not
# proof of runtime health or authorization.
CAPABILITY_RULES: tuple[dict[str, Any], ...] = (
    {
        "id": "local_python_runtime",
        "description": "Run Python modules in the current local environment",
        "evidence": "python_runtime",
        "level": "LOCAL_RUNTIME_PRESENT",
    },
    {
        "id": "brain_tool_foundry",
        "description": "Validate and scaffold inert Brain tool proposals",
        "evidence": "tool_foundry_source",
        "level": "SOURCE_PRESENT_RUNTIME_UNVERIFIED",
    },
    {
        "id": "media_transcoding",
        "description": "Transcode media with FFmpeg and inspect media with FFprobe",
        "evidence": "media_tools",
        "level": "LOCAL_TOOLS_PRESENT_RUNTIME_UNVERIFIED",
    },
    {
        "id": "android_bridge",
        "description": "Use Android Debug Bridge from this host",
        "evidence": "adb",
        "level": "LOCAL_TOOL_PRESENT_RUNTIME_UNVERIFIED",
    },
    {
        "id": "rtl_simulation",
        "description": "Run at least one supported RTL simulator",
        "evidence": "rtl_tools",
        "level": "LOCAL_TOOL_PRESENT_RUNTIME_UNVERIFIED",
    },
    {
        "id": "windows_virtualization_tools",
        "description": "Use QEMU tools for virtual-machine workflows",
        "evidence": "qemu_tools",
        "level": "LOCAL_TOOLS_PRESENT_RUNTIME_UNVERIFIED",
    },
    {
        "id": "remote_device_execution",
        "description": "Execute a task on an authenticated remote Brain device",
        "evidence": "remote_device_attestation",
        "level": "REQUIRES_LIVE_AUTHENTICATED_DEVICE_EVIDENCE",
    },
    {
        "id": "physical_mining",
        "description": "Verify a real mining worker connected to Braiins Pool",
        "evidence": "pool_worker_telemetry",
        "level": "REQUIRES_INDEPENDENT_POOL_AND_DEVICE_EVIDENCE",
    },
)


def _bool_lookup(items: list[dict[str, Any]], name: str) -> bool:
    return any(item.get("name") == name and item.get("available") is True for item in items)


def audit(inventory: dict[str, Any] | None = None) -> dict[str, Any]:
    """Compare observed local facts with capability requirements."""
    inventory = inventory or discover()
    modules = inventory.get("python_modules", [])
    executables = inventory.get("executables", [])
    components = inventory.get("brain_components", [])
    component_map = {x.get("path"): x.get("present") is True for x in components}
    python_path = inventory.get("host", {}).get("python_executable")
    rules_evidence: dict[str, tuple[bool, str]] = {
        "python_runtime": (bool(python_path), "Python executable path was reported by the running interpreter."),
        "tool_foundry_source": (
            component_map.get("brain_v12/brain/tool_foundry.py", False),
            "Source-file presence only; tests and runtime health remain unverified.",
        ),
        "media_tools": (
            _bool_lookup(executables, "ffmpeg") and _bool_lookup(executables, "ffprobe"),
            "Both ffmpeg and ffprobe must be found on PATH; runtime smoke test is still required.",
        ),
        "adb": (
            _bool_lookup(executables, "adb"),
            "ADB executable presence only; no device was probed.",
        ),
        "rtl_tools": (
            _bool_lookup(executables, "iverilog") or _bool_lookup(executables, "verilator"),
            "At least one RTL simulator executable must be found; no simulation was run.",
        ),
        "qemu_tools": (
            _bool_lookup(executables, "qemu-system-x86_64") and _bool_lookup(executables, "qemu-img"),
            "Both QEMU executables must be found; no VM was started.",
        ),
        "remote_device_attestation": (False, "No live authenticated device attestation is consumed by this local audit."),
        "pool_worker_telemetry": (False, "Local software inventory cannot prove pool worker activity or real hashrate."),
    }
    results = []
    for rule in CAPABILITY_RULES:
        present, note = rules_evidence[rule["evidence"]]
        if rule["evidence"] in {"remote_device_attestation", "pool_worker_telemetry"}:
            status = "BLOCKED_NEEDS_EXTERNAL_EVIDENCE"
        elif present:
            status = "OBSERVED_NOT_YET_RUNTIME_VERIFIED"
        else:
            status = "MISSING_LOCAL_REQUIREMENT"
        results.append({
            "capability_id": rule["id"],
            "description": rule["description"],
            "status": status,
            "observed_present": present,
            "evidence_level": rule["level"],
            "note": note,
        })

    gaps = [x for x in results if x["status"] != "OBSERVED_NOT_YET_RUNTIME_VERIFIED"]
    return {
        "schema": "brain-capability-gap-audit/v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": "PLAN_ONLY_NO_REGISTRATION",
        "inventory_schema": inventory.get("schema"),
        "capability_registry_mutated": False,
        "generated_code_executed": False,
        "network_probed": False,
        "mining_enabled": False,
        "capabilities": results,
        "gap_count": len(gaps),
        "gaps": gaps,
        "next_action": (
            "Create a reviewed, narrow-scope proposal for missing local capabilities; "
            "collect independent authenticated evidence for remote devices and mining."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="Optional new JSON report path; refuses overwrite.")
    args = parser.parse_args(argv)
    report = audit()
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output).expanduser().resolve()
        if output.exists():
            parser.error(f"refusing to overwrite existing file: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
