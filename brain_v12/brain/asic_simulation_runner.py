"""Explicit ASIC logic-simulator adapter that records simulation evidence only."""
from __future__ import annotations

from typing import Any

from brain_v12.business.mining_activity_ledger import MiningActivityLedger
from brain_v12.brain.asic_hardware_simulator import ASICLogicSimulator


def run_and_record_asic_simulation(
    netlist: dict[str, Any],
    vectors: list[dict[str, Any]],
    *,
    activity_id: str,
    run_id: str,
    ledger: MiningActivityLedger,
    max_cycles: int = 10_000,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run the digital simulator explicitly and persist its returned report."""
    report = ASICLogicSimulator(netlist).run(vectors, max_cycles=max_cycles)
    activity = ledger.record(
        activity_id=activity_id,
        run_id=run_id,
        mode="SIMULATION",
        activity_type="SIMULATOR_RUN",
        source="brain_v12.brain.asic_simulation_runner",
        evidence_ref=f"asic-simulation:{run_id}",
        payload={
            "simulator": report["simulator"],
            "version": report["version"],
            "model": report["model"],
            "cycles": report["cycles"],
            "clock_hz": report["clock_hz"],
            "elapsed_seconds": report["elapsed_seconds"],
            "node_count": report["node_count"],
            "summary": report["summary"],
            "limitations": report["limitations"],
        },
    )
    return report, activity
