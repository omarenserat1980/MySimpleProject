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


    def checkpoint(self) -> dict:
        """Serialize programs and all scheduler state for deterministic resume."""
        return {
            "schema": "brainvm-runner-snapshot-v1",
            "mode": "SIMULATED_BRAINVM_TASK_RUNNER",
            "ram_cells": self.ram_cells,
            "clock_width_bits": self.clock_width_bits,
            "cursor": self._cursor,
            "kernel": {
                "ticks": self.kernel.ticks,
                "interrupts": [dict(event) for event in self.kernel.interrupts],
                "syscalls": [dict(event) for event in self.kernel.syscalls],
            },
            "tasks": [
                {
                    "pid": pid,
                    "name": task["process"].name,
                    "state": task["process"].state,
                    "process_ticks": task["process"].ticks,
                    "program": [list(instruction) for instruction in task["program"]],
                    "board": task["board"].checkpoint(),
                    "steps": task["steps"],
                }
                for pid, task in self._tasks.items()
            ],
            "task_programs_included": True,
            "physical_hardware": False,
            "native_code_execution": False,
        }

    def restore_checkpoint(self, checkpoint: dict) -> dict:
        """Validate into a fresh runner, then atomically replace this runner's state."""
        if not isinstance(checkpoint, dict) or checkpoint.get("schema") != "brainvm-runner-snapshot-v1":
            raise ValueError("TASK_RUNNER_CHECKPOINT_SCHEMA_UNSUPPORTED")
        if checkpoint.get("mode") != "SIMULATED_BRAINVM_TASK_RUNNER" or checkpoint.get("task_programs_included") is not True:
            raise ValueError("TASK_RUNNER_CHECKPOINT_MODE_OR_PROGRAMS_INVALID")
        try:
            ram_cells = checkpoint["ram_cells"]
            width = checkpoint["clock_width_bits"]
            cursor = checkpoint["cursor"]
            kernel_data = checkpoint["kernel"]
            tasks_data = checkpoint["tasks"]
            ticks = kernel_data["ticks"]
            interrupts = kernel_data["interrupts"]
            syscalls = kernel_data["syscalls"]
        except (KeyError, TypeError) as exc:
            raise ValueError("TASK_RUNNER_CHECKPOINT_MALFORMED") from exc
        for value, code in ((ram_cells, "RAM"), (width, "CLOCK"), (cursor, "CURSOR"), (ticks, "TICKS")):
            if not isinstance(value, int) or isinstance(value, bool) or value < (1 if code in ("RAM", "CLOCK") else 0):
                raise ValueError("TASK_RUNNER_CHECKPOINT_" + code + "_INVALID")
        if not isinstance(tasks_data, list) or not isinstance(interrupts, list) or not isinstance(syscalls, list):
            raise ValueError("TASK_RUNNER_CHECKPOINT_COLLECTION_INVALID")
        if any(not isinstance(event, dict) for event in interrupts + syscalls):
            raise ValueError("TASK_RUNNER_CHECKPOINT_EVENT_INVALID")
        if len({item.get("pid") for item in tasks_data if isinstance(item, dict)} ) != len(tasks_data):
            raise ValueError("TASK_RUNNER_CHECKPOINT_PID_DUPLICATE")
        candidate = BrainVMTaskRunner(ram_cells=ram_cells, clock_width_bits=width)
        candidate.kernel.ticks = ticks
        candidate.kernel.interrupts = [dict(event) for event in interrupts]
        candidate.kernel.syscalls = [dict(event) for event in syscalls]
        for item in tasks_data:
            if not isinstance(item, dict):
                raise ValueError("TASK_RUNNER_CHECKPOINT_TASK_INVALID")
            try:
                pid, name, state = item["pid"], item["name"], item["state"]
                process_ticks, program, board_data, steps = item["process_ticks"], item["program"], item["board"], item["steps"]
            except (KeyError, TypeError) as exc:
                raise ValueError("TASK_RUNNER_CHECKPOINT_TASK_MALFORMED") from exc
            if not isinstance(pid, str) or not pid or state not in ("READY", "RUNNING", "TERMINATED"):
                raise ValueError("TASK_RUNNER_CHECKPOINT_PROCESS_INVALID")
            for value in (process_ticks, steps):
                if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                    raise ValueError("TASK_RUNNER_CHECKPOINT_COUNTER_INVALID")
            if not isinstance(program, list) or not program:
                raise ValueError("TASK_RUNNER_CHECKPOINT_PROGRAM_INVALID")
            for instruction in program:
                if (not isinstance(instruction, list) or not instruction or not isinstance(instruction[0], str)
                    or any(not isinstance(arg, (str, int)) or isinstance(arg, bool) for arg in instruction)):
                    raise ValueError("TASK_RUNNER_CHECKPOINT_INSTRUCTION_INVALID")
            if not isinstance(name, str) or not name.strip():
                raise ValueError("TASK_RUNNER_CHECKPOINT_NAME_INVALID")
            if not isinstance(board_data, dict):
                raise ValueError("TASK_RUNNER_CHECKPOINT_BOARD_INVALID")
            candidate_pid = candidate.create_task(name, program)
            task = candidate._tasks.pop(candidate_pid)
            process = task["process"]
            candidate.kernel.processes.pop(candidate_pid, None)
            process.pid = pid
            process.state = state
            process.ticks = process_ticks
            candidate.kernel.processes[pid] = process
            task["program"] = tuple(tuple(instruction) for instruction in program)
            task["board"].restore_checkpoint(board_data)
            task["steps"] = steps
            if steps != task["board"].instructions_executed:
                raise ValueError("TASK_RUNNER_CHECKPOINT_STEP_COUNT_MISMATCH")
            if state == "TERMINATED" and not task["board"].cpu.halted:
                raise ValueError("TASK_RUNNER_CHECKPOINT_TERMINATED_TASK_NOT_HALTED")
            if state != "TERMINATED" and task["board"].cpu.halted:
                raise ValueError("TASK_RUNNER_CHECKPOINT_HALTED_TASK_NOT_TERMINATED")
            candidate._tasks[pid] = task
        if interrupts and any(not isinstance(event.get("tick"), int) or event["tick"] < 0 for event in interrupts):
            raise ValueError("TASK_RUNNER_CHECKPOINT_INTERRUPT_TICK_INVALID")
        if any(event.get("tick", 0) > ticks for event in interrupts):
            raise ValueError("TASK_RUNNER_CHECKPOINT_INTERRUPT_IN_FUTURE")
        if cursor < 0:
            raise ValueError("TASK_RUNNER_CHECKPOINT_CURSOR_INVALID")
        candidate._cursor = cursor
        self.ram_cells = candidate.ram_cells
        self.clock_width_bits = candidate.clock_width_bits
        self.kernel = candidate.kernel
        self._tasks = candidate._tasks
        self._cursor = candidate._cursor
        return self.status()
