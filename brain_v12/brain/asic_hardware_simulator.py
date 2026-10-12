"""Inspectable digital ASIC netlist simulator for Brain V12.

This is a deterministic, software-only logic simulator, not a transistor/SPICE,
physical-layout, or measured-device simulator. All assumptions are included in
each report. Combinational nodes are evaluated from the declared netlist;
DFF nodes update synchronously at the end of each cycle.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SIMULATOR_VERSION = "0.1.0"
OPS = {"INPUT", "CONST", "NOT", "BUF", "AND", "OR", "XOR", "NAND", "NOR", "XNOR", "MUX", "DFF"}
MAX_NODES = 512
MAX_CYCLES = 10000


class ASICSimulationError(ValueError):
    """Invalid netlist or unsupported simulation state."""


@dataclass(frozen=True)
class Node:
    name: str
    op: str
    inputs: tuple[str, ...] = ()
    value: int | None = None


class ASICLogicSimulator:
    """Cycle-accurate digital logic simulator with deterministic event traces."""

    def __init__(self, netlist: dict[str, Any]):
        if not isinstance(netlist, dict):
            raise ASICSimulationError("NETLIST_MUST_BE_OBJECT")
        raw_nodes = netlist.get("nodes")
        if not isinstance(raw_nodes, list) or not raw_nodes or len(raw_nodes) > MAX_NODES:
            raise ASICSimulationError("NODES_REQUIRED_OR_LIMIT_EXCEEDED")
        self.clock_hz = self._number(netlist.get("clock_hz", 1_000_000), "INVALID_CLOCK_HZ", minimum=1)
        self.energy_per_toggle_pj = self._number(netlist.get("energy_per_toggle_pj", 0), "INVALID_ENERGY_PER_TOGGLE", minimum=0)
        self.nodes: list[Node] = []
        names: set[str] = set()
        for raw in raw_nodes:
            if not isinstance(raw, dict):
                raise ASICSimulationError("NODE_MUST_BE_OBJECT")
            name = raw.get("name")
            op = str(raw.get("op", "")).upper()
            inputs = raw.get("inputs", [])
            if not isinstance(name, str) or not name or name in names:
                raise ASICSimulationError("NODE_NAME_MISSING_OR_DUPLICATE")
            if op not in OPS:
                raise ASICSimulationError("UNSUPPORTED_OP:" + op)
            if not isinstance(inputs, list) or any(not isinstance(x, str) for x in inputs):
                raise ASICSimulationError("NODE_INPUTS_MUST_BE_NAMES")
            expected = {"INPUT": 0, "CONST": 0, "NOT": 1, "BUF": 1, "AND": 2, "OR": 2,
                        "XOR": 2, "NAND": 2, "NOR": 2, "XNOR": 2, "MUX": 3, "DFF": 1}[op]
            if len(inputs) != expected:
                raise ASICSimulationError("INVALID_INPUT_COUNT:" + name)
            value = raw.get("value")
            if op == "CONST" and value not in (0, 1, False, True):
                raise ASICSimulationError("CONST_VALUE_MUST_BE_0_OR_1")
            if op == "INPUT" and value is not None:
                raise ASICSimulationError("INPUT_DEFAULT_NOT_SUPPORTED")
            self.nodes.append(Node(name, op, tuple(inputs), int(value) if value is not None else None))
            names.add(name)
        for node in self.nodes:
            for source in node.inputs:
                if source not in names:
                    raise ASICSimulationError("UNKNOWN_INPUT:" + source)
        outputs = netlist.get("outputs", [])
        if not isinstance(outputs, list) or any(x not in names for x in outputs):
            raise ASICSimulationError("INVALID_OUTPUTS")
        self.outputs = outputs or [self.nodes[-1].name]
        self.by_name = {node.name: node for node in self.nodes}
        self._validate_combinational_graph()
        self.state = {node.name: 0 for node in self.nodes if node.op == "DFF"}
        self.previous_values: dict[str, int] = {}
        self.total_toggles = 0
        self.total_cycles = 0

    @staticmethod
    def _number(value: Any, error: str, minimum: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < minimum:
            raise ASICSimulationError(error)
        if value == float("inf") or value != value:
            raise ASICSimulationError(error)
        return float(value)

    def _validate_combinational_graph(self) -> None:
        # A DFF breaks a combinational path. Every other node must be evaluable
        # from INPUT/CONST nodes and DFF outputs without a combinational loop.
        pending = {n.name for n in self.nodes if n.op not in {"INPUT", "CONST", "DFF"}}
        ready = {n.name for n in self.nodes if n.op in {"INPUT", "CONST", "DFF"}}
        changed = True
        while changed:
            changed = False
            for name in tuple(pending):
                if all(src in ready for src in self.by_name[name].inputs):
                    pending.remove(name)
                    ready.add(name)
                    changed = True
        if pending:
            raise ASICSimulationError("COMBINATIONAL_LOOP_OR_DEPENDENCY:" + ",".join(sorted(pending)))
        for node in self.nodes:
            if node.op == "DFF" and node.inputs[0] == node.name:
                raise ASICSimulationError("DFF_SELF_INPUT:" + node.name)

    @staticmethod
    def _bit(value: Any, label: str) -> int:
        if value not in (0, 1, False, True):
            raise ASICSimulationError("SIGNAL_MUST_BE_0_OR_1:" + label)
        return int(value)

    def _evaluate(self, node: Node, values: dict[str, int]) -> int:
        a = [values[x] for x in node.inputs]
        if node.op == "NOT": return 1 - a[0]
        if node.op == "BUF": return a[0]
        if node.op == "AND": return a[0] & a[1]
        if node.op == "OR": return a[0] | a[1]
        if node.op == "XOR": return a[0] ^ a[1]
        if node.op == "NAND": return 1 - (a[0] & a[1])
        if node.op == "NOR": return 1 - (a[0] | a[1])
        if node.op == "XNOR": return 1 - (a[0] ^ a[1])
        if node.op == "MUX": return a[1] if a[0] else a[2]
        raise ASICSimulationError("NOT_COMBINATIONAL:" + node.name)

    def step(self, inputs: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(inputs, dict):
            raise ASICSimulationError("INPUTS_MUST_BE_OBJECT")
        input_nodes = {n.name for n in self.nodes if n.op == "INPUT"}
        if set(inputs) != input_nodes:
            missing, extra = sorted(input_nodes - set(inputs)), sorted(set(inputs) - input_nodes)
            raise ASICSimulationError("INPUT_SET_MISMATCH:missing=" + ",".join(missing) + ";extra=" + ",".join(extra))
        values: dict[str, int] = {}
        for node in self.nodes:
            if node.op == "INPUT":
                values[node.name] = self._bit(inputs[node.name], node.name)
            elif node.op == "CONST":
                values[node.name] = int(node.value or 0)
            elif node.op == "DFF":
                values[node.name] = self.state[node.name]
        pending = {n.name for n in self.nodes if n.op not in {"INPUT", "CONST", "DFF"}}
        while pending:
            progressed = False
            for node in self.nodes:
                if node.name in pending and all(source in values for source in node.inputs):
                    values[node.name] = self._evaluate(node, values)
                    pending.remove(node.name)
                    progressed = True
            if not progressed:
                raise ASICSimulationError("UNRESOLVED_COMBINATIONAL_DEPENDENCY")
        next_state = {n.name: values[n.inputs[0]] for n in self.nodes if n.op == "DFF"}
        toggled = sorted(name for name, value in values.items()
                         if name in self.previous_values and self.previous_values[name] != value)
        self.total_toggles += len(toggled)
        self.total_cycles += 1
        cycle = self.total_cycles
        self.state = next_state
        self.previous_values = dict(values)
        elapsed = cycle / self.clock_hz
        dynamic_energy_j = self.total_toggles * self.energy_per_toggle_pj * 1e-12
        return {
            "cycle": cycle, "time_seconds": elapsed, "inputs": dict(inputs),
            "signals": dict(values), "outputs": {name: values[name] for name in self.outputs},
            "dff_next_state": dict(next_state), "toggled_signals_this_cycle": toggled,
            "toggle_count_this_cycle": len(toggled), "cumulative_toggle_count": self.total_toggles,
            "estimated_dynamic_energy_j": dynamic_energy_j,
            "estimated_average_dynamic_power_w": dynamic_energy_j / elapsed if elapsed else 0.0,
            "model": "IDEAL_2_STATE_DIGITAL", "real_hardware_measurement": False,
        }

    def run(self, vectors: list[dict[str, Any]], *, max_cycles: int = MAX_CYCLES) -> dict[str, Any]:
        if not isinstance(vectors, list) or not vectors:
            raise ASICSimulationError("INPUT_VECTORS_REQUIRED")
        if isinstance(max_cycles, bool) or not isinstance(max_cycles, int) or not 1 <= max_cycles <= MAX_CYCLES:
            raise ASICSimulationError("INVALID_MAX_CYCLES")
        if len(vectors) > max_cycles:
            raise ASICSimulationError("CYCLE_LIMIT_EXCEEDED")
        trace = [self.step(vector) for vector in vectors]
        return {
            "ok": True, "simulator": "Brain ASIC Logic Simulator", "version": SIMULATOR_VERSION,
            "model": "IDEAL_2_STATE_DIGITAL", "cycles": self.total_cycles,
            "clock_hz": self.clock_hz, "elapsed_seconds": self.total_cycles / self.clock_hz,
            "node_count": len(self.nodes), "node_inventory": [
                {"name": n.name, "op": n.op, "inputs": list(n.inputs), "value": n.value} for n in self.nodes
            ],
            "outputs": list(self.outputs), "trace": trace,
            "summary": {"toggle_count": self.total_toggles,
                        "estimated_dynamic_energy_j": self.total_toggles * self.energy_per_toggle_pj * 1e-12,
                        "real_hardware_measurement": False},
            "limitations": [
                "Ideal two-state digital logic only; no X/Z propagation.",
                "No transistor-level SPICE, analog behavior, metastability, setup/hold, routing delay, or physical layout.",
                "Energy is an optional user-supplied per-toggle estimate, not calibrated silicon power.",
                "DFFs update synchronously after combinational evaluation; no asynchronous reset or edge timing model.",
                "This software simulation does not claim measured ASIC performance."
            ],
        }
