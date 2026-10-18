"""Run a bounded Brain memory trace through the pinned Ramulator 2 Python API.

This produces simulation evidence only; it is not a physical RAM measurement.
"""
from __future__ import annotations

import os
from pathlib import Path

import ramulator

trace_path = Path(os.environ["BRAIN_RAMULATOR_TRACE"]).resolve(strict=True)
if not trace_path.is_file() or trace_path.stat().st_size > 1_048_576:
    raise SystemExit("BRAIN_TRACE_INVALID_SIZE_OR_TYPE")

lines = [
    line.strip()
    for line in trace_path.read_text(encoding="utf-8").splitlines()
    if line.strip() and not line.lstrip().startswith("#")
]
if not lines:
    raise SystemExit("BRAIN_TRACE_EMPTY")

# Validate the SimpleO3 trace format before passing it to upstream code.
for line_no, line in enumerate(lines, start=1):
    fields = line.split()
    if len(fields) not in (2, 3):
        raise SystemExit(f"BRAIN_TRACE_BAD_FIELD_COUNT:{line_no}")
    try:
        op = int(fields[0], 10)
        addresses = [int(value, 10) for value in fields[1:]]
    except ValueError as exc:
        raise SystemExit(f"BRAIN_TRACE_NON_INTEGER:{line_no}") from exc
    if not 0 <= op <= 8 or any(address < 0 or address >= 2**31 for address in addresses):
        raise SystemExit(f"BRAIN_TRACE_OUT_OF_RANGE:{line_no}")

frontend = ramulator.frontend.SimpleO3(
    clock_ratio=8,
    traces=[str(trace_path)],
    num_expected_insts=len(lines),
    translation=ramulator.translation.NoTranslation(max_addr=2147483648),
)
dram = ramulator.dram.DDR4(
    org_preset="DDR4_8Gb_x8",
    timing_preset="DDR4_2400R",
    rank=1,
    verbose=False,
)
controller = ramulator.controller.GenericDDR(
    dram=dram,
    scheduler=ramulator.scheduler.FRFCFS(),
    refresh_manager=ramulator.refresh_manager.AllBank(),
    row_policy=ramulator.row_policy.Open(),
    addr_mapper=ramulator.addr_mapper.RoBaRaCoCh(),
)
memory = ramulator.memory_system.GenericDRAM(
    clock_ratio=3,
    controllers=[controller],
    channel_mapper=ramulator.channel_mapper.CacheLineInterleave(),
)
simulation = ramulator.Simulation(frontend, memory)
simulation.run()
stats = simulation.stats
if not stats:
    raise SystemExit("BRAIN_RAMULATOR_EMPTY_STATS")
ctrl = stats["memory_system"]["controller"]
cycles = int(ctrl["cycles"])
reads = int(ctrl["num_read_reqs"])
writes = int(ctrl["num_write_reqs"])
if cycles <= 0 or reads + writes <= 0:
    raise SystemExit("BRAIN_RAMULATOR_NO_MEMORY_ACTIVITY")
print(f"Brain trace records: {len(lines)}")
print(f"Controller cycles: {cycles}")
print(f"Avg read latency: {float(ctrl['avg_read_latency']):.1f} cycles")
print(f"Read requests: {reads}")
print(f"Write requests: {writes}")
print(f"Row hits: {int(ctrl['row_hits'])}")
print(f"Row misses: {int(ctrl['row_misses'])}")
print(f"Row conflicts: {int(ctrl['row_conflicts'])}")
print("Evidence class: UPSTREAM_TOOL_EXECUTION_SIMULATION_ONLY")
print("Physical RAM verified: false")
