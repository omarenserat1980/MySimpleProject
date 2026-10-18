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

    def checkpoint(self) -> dict:
        """Return a JSON-compatible snapshot for deterministic simulation resume."""
        return {
            "schema": "brainvm-board-checkpoint-v1",
            "mode": "SIMULATED_BRAINVM_BOARD",
            "clock": {"width_bits": self.clock.width_bits, "ticks": self.clock.ticks,
                      "enabled": self.clock.enabled},
            "cpu": {
                "profile_name": self.cpu.profile_name,
                "registers": list(self.cpu.registers),
                "pc": self.cpu.pc,
                "zero": self.cpu.zero,
                "negative": self.cpu.negative,
                "carry": self.cpu.carry,
                "overflow": self.cpu.overflow,
                "halted": self.cpu.halted,
                "cycles": self.cpu.cycles,
                "output": list(self.cpu.output),
            },
            "ram": self.ram.snapshot(),
            "instructions_executed": self.instructions_executed,
            "physical_hardware": False,
        }

    def restore_checkpoint(self, checkpoint: dict) -> dict:
        """Restore only a validated BrainVM simulation checkpoint; never executes host code."""
        if not isinstance(checkpoint, dict) or checkpoint.get("schema") != "brainvm-board-checkpoint-v1":
            raise ValueError("BOARD_CHECKPOINT_SCHEMA_UNSUPPORTED")
        if checkpoint.get("mode") != "SIMULATED_BRAINVM_BOARD":
            raise ValueError("BOARD_CHECKPOINT_MODE_INVALID")
        try:
            clock = checkpoint["clock"]
            cpu = checkpoint["cpu"]
            ram_snapshot = checkpoint["ram"]
            width = int(clock["width_bits"])
            ticks = int(clock["ticks"])
            enabled = clock["enabled"]
            registers = cpu["registers"]
            pc = int(cpu["pc"])
            cycles = int(cpu["cycles"])
            instructions = int(checkpoint["instructions_executed"])
            output = cpu["output"]
            profile_name = cpu["profile_name"]
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("BOARD_CHECKPOINT_MALFORMED") from exc
        if not isinstance(enabled, bool) or not isinstance(registers, list) or len(registers) != 8:
            raise ValueError("BOARD_CHECKPOINT_CPU_OR_CLOCK_INVALID")
        if any(not isinstance(value, int) or isinstance(value, bool) for value in registers):
            raise ValueError("BOARD_CHECKPOINT_REGISTERS_INVALID")
        if pc < 0 or cycles < 0 or instructions < 0 or not isinstance(output, list):
            raise ValueError("BOARD_CHECKPOINT_COUNTER_INVALID")
        if any(not isinstance(value, int) or isinstance(value, bool) for value in output):
            raise ValueError("BOARD_CHECKPOINT_OUTPUT_INVALID")
        # Build candidate objects first so malformed input cannot partially overwrite live state.
        candidate_cpu = VirtualCPU(profile_name=profile_name)
        candidate_cpu.registers = list(registers)
        candidate_cpu.pc = pc
        candidate_cpu.zero = bool(cpu.get("zero", False))
        candidate_cpu.negative = bool(cpu.get("negative", False))
        candidate_cpu.carry = bool(cpu.get("carry", False))
        candidate_cpu.overflow = bool(cpu.get("overflow", False))
        candidate_cpu.halted = bool(cpu.get("halted", False))
        candidate_cpu.cycles = cycles
        candidate_cpu.output = list(output)
        candidate_ram = VirtualRAM(self.ram.size)
        candidate_ram.restore(ram_snapshot)
        candidate_clock = DigitalClock(width_bits=width, ticks=ticks, enabled=enabled)
        self.cpu = candidate_cpu
        self.ram = candidate_ram
        self.clock = candidate_clock
        self.instructions_executed = instructions
        return self.status()

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
