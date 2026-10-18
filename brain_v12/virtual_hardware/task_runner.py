"""Deterministic round-robin runner for isolated BrainVM software processes.

All tasks execute BrainVM tuples in simulated CPU/RAM. This runner does not
execute native code, launch host processes, or represent physical hardware.
"""
from __future__ import annotations

from .execution_board import BrainVMExecutionBoard
from .kernel import VirtualKernel


class BrainVMTaskRunner:
    """Run isolated BrainVM programs one instruction per scheduler quantum."""

    def __init__(self, ram_cells: int = 65536, clock_width_bits: int = 32):
        if not isinstance(ram_cells, int) or isinstance(ram_cells, bool) or ram_cells <= 0:
            raise ValueError("TASK_RUNNER_RAM_CELLS_MUST_BE_POSITIVE")
        if not isinstance(clock_width_bits, int) or isinstance(clock_width_bits, bool) or clock_width_bits <= 0:
            raise ValueError("TASK_RUNNER_CLOCK_WIDTH_MUST_BE_POSITIVE")
        self.ram_cells = ram_cells
        self.clock_width_bits = clock_width_bits
        self.kernel = VirtualKernel()
        self._tasks = {}
        self._cursor = 0

    def create_task(self, name: str, program) -> str:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("TASK_NAME_REQUIRED")
        if not isinstance(program, (list, tuple)) or not program:
            raise ValueError("TASK_PROGRAM_MUST_BE_NONEMPTY")
        if any(not isinstance(instruction, (list, tuple)) or not instruction
               or not isinstance(instruction[0], str) for instruction in program):
            raise ValueError("TASK_PROGRAM_INSTRUCTION_INVALID")
        if any(task["process"].name == name and task["process"].state != "TERMINATED"
               for task in self._tasks.values()):
            raise ValueError("TASK_NAME_ALREADY_ACTIVE")
        process = self.kernel.create_process(name.strip())
        self._tasks[process.pid] = {
            "process": process,
            "program": tuple(tuple(instruction) for instruction in program),
            "board": BrainVMExecutionBoard(
                ram_cells=self.ram_cells, clock_width_bits=self.clock_width_bits
            ),
            "steps": 0,
        }
        return process.pid

    def run(self, max_ticks: int = 10000) -> dict:
        if not isinstance(max_ticks, int) or isinstance(max_ticks, bool) or max_ticks <= 0:
            raise ValueError("TASK_RUNNER_TICK_BUDGET_MUST_BE_POSITIVE")
        trace = []
        for _ in range(max_ticks):
            runnable = [
                pid for pid, task in self._tasks.items()
                if task["process"].state != "TERMINATED" and not task["board"].cpu.halted
            ]
            if not runnable:
                break
            self._cursor %= len(runnable)
            pid = runnable[self._cursor]
            self._cursor = (self._cursor + 1) % len(runnable)
            task = self._tasks[pid]
            process = task["process"]
            process.state = "RUNNING"
            step = task["board"].step(task["program"])
            task["steps"] += 1
            self.kernel.ticks += 1
            process.ticks += 1
            self.kernel.interrupts.append({"type": "TIMER", "tick": self.kernel.ticks})
            trace.append({
                "tick": self.kernel.ticks,
                "pid": pid,
                "task": process.name,
                "pc": task["board"].cpu.pc,
                "step": step,
            })
            if task["board"].cpu.halted:
                self.kernel.terminate(pid)
            else:
                process.state = "READY"
        active = [
            task for task in self._tasks.values()
            if task["process"].state != "TERMINATED" and not task["board"].cpu.halted
        ]
        return {
            "ok": True,
            "mode": "SIMULATED_BRAINVM_TASK_RUNNER",
            "ticks_this_run": len(trace),
            "total_ticks": self.kernel.ticks,
            "completed": not active,
            "active_tasks": [task["process"].name for task in active],
            "tasks": [
                {
                    "pid": pid,
                    "name": task["process"].name,
                    "state": task["process"].state,
                    "instructions_executed": task["steps"],
                    "cpu_halted": task["board"].cpu.halted,
                    "cpu_pc": task["board"].cpu.pc,
                    "output": list(task["board"].cpu.output),
                    "clock": task["board"].clock.status(),
                    "ram": task["board"].ram.snapshot(),
                }
                for pid, task in self._tasks.items()
            ],
            "kernel": self.kernel.status(),
            "trace": trace,
            "physical_hardware": False,
            "native_code_execution": False,
        }

    def status(self) -> dict:
        return {
            "mode": "SIMULATED_BRAINVM_TASK_RUNNER",
            "task_count": len(self._tasks),
            "kernel": self.kernel.status(),
            "physical_hardware": False,
        }
