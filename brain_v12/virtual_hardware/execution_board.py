"""Clocked BrainVM board: deterministic integration of CPU, RAM, and logical clock.

This is a software simulation. One logical tick is assigned per successfully
executed instruction; it is not a physical clock cycle or performance measurement.
"""
from __future__ import annotations

from .cpu import VirtualCPU
from .digital_logic import DigitalClock
from .memory import VirtualRAM


class BrainVMExecutionBoard:
    """Minimal integrated board for bounded BrainVM program execution."""
    def __init__(self, ram_cells: int = 65536, clock_width_bits: int = 32,
                 cpu: VirtualCPU | None = None):
        if not isinstance(ram_cells, int) or ram_cells <= 0:
            raise ValueError("BOARD_RAM_CELLS_MUST_BE_POSITIVE")
        self.cpu = cpu or VirtualCPU()
        self.ram = VirtualRAM(ram_cells)
        self.clock = DigitalClock(width_bits=clock_width_bits)
        self.instructions_executed = 0

    def reset(self) -> dict:
        self.cpu.reset()
        self.ram = VirtualRAM(self.ram.size)
        self.clock.reset()
        self.instructions_executed = 0
        return self.status()

    def run(self, program, max_instructions: int = 10000) -> dict:
        if not isinstance(max_instructions, int) or max_instructions <= 0:
            raise ValueError("BOARD_INSTRUCTION_BUDGET_MUST_BE_POSITIVE")
        trace = []
        while not self.cpu.halted and len(trace) < max_instructions:
            step = self.cpu.step(program, self.ram)
            self.clock.pulse()
            self.instructions_executed += 1
            trace.append(step)
        if not self.cpu.halted:
            raise RuntimeError("BOARD_INSTRUCTION_BUDGET_EXHAUSTED")
        return {
            "ok": True,
            "mode": "SIMULATED_BRAINVM_BOARD",
            "instructions_executed_this_run": len(trace),
            "total_instructions_executed": self.instructions_executed,
            "clock": self.clock.status(),
            "cpu": {
                "halted": self.cpu.halted,
                "pc": self.cpu.pc,
                "cycles": self.cpu.cycles,
                "registers": list(self.cpu.registers),
                "output": list(self.cpu.output),
                "flags": {
                    "zero": self.cpu.zero,
                    "negative": self.cpu.negative,
                    "carry": self.cpu.carry,
                    "overflow": self.cpu.overflow,
                },
            },
            "ram": self.ram.snapshot(),
            "trace": trace,
            "physical_hardware": False,
            "physical_performance_measurement": False,
        }

    def status(self) -> dict:
        return {
            "mode": "SIMULATED_BRAINVM_BOARD",
            "clock": self.clock.status(),
            "cpu_halted": self.cpu.halted,
            "cpu_pc": self.cpu.pc,
            "cpu_cycles": self.cpu.cycles,
            "ram_cells": self.ram.size,
            "ram_used_cells": self.ram.used_cells,
            "total_instructions_executed": self.instructions_executed,
            "physical_hardware": False,
        }
