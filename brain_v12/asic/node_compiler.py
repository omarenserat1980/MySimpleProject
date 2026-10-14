"""Deterministic compiler for a small, declarative hardware-node graph.

This first version emits combinational SystemVerilog only. Generated RTL is a
design artifact; it is not proof of simulation, synthesis, device programming,
or physical fabrication.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_OPERATORS = {
    "add": (2, lambda args: f"{args[0]} + {args[1]}"),
    "sub": (2, lambda args: f"{args[0]} - {args[1]}"),
    "and": (2, lambda args: f"{args[0]} & {args[1]}"),
    "or": (2, lambda args: f"{args[0]} | {args[1]}"),
    "xor": (2, lambda args: f"{args[0]} ^ {args[1]}"),
    "not": (1, lambda args: f"~{args[0]}"),
    "pass": (1, lambda args: args[0]),
}


class NodeCompileError(ValueError):
    """Raised when a node graph is invalid or unsafe to compile."""


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise NodeCompileError(f"INVALID_IDENTIFIER:{label}")
    if value.startswith("__"):
        raise NodeCompileError(f"RESERVED_IDENTIFIER:{label}")
    return value


def compile_graph(spec: dict[str, Any]) -> str:
    """Compile a validated node graph to synthesizable combinational SystemVerilog.

    Schema:
      module: identifier
      width: integer 1..256
      inputs: list of port identifiers
      nodes: ordered list of {id, op, inputs} or {id, op:"const", value}
      outputs: mapping of output-port identifier to an input/node identifier

    References must point to inputs or earlier nodes. This makes ordering and
    cycle rejection deterministic without executing arbitrary user code.
    """
    if not isinstance(spec, dict):
        raise NodeCompileError("SPEC_MUST_BE_OBJECT")
    allowed_top = {"module", "width", "inputs", "nodes", "outputs"}
    unknown = set(spec) - allowed_top
    if unknown:
        raise NodeCompileError("UNKNOWN_SPEC_FIELDS:" + ",".join(sorted(map(str, unknown))))
    module = _identifier(spec.get("module"), "module")
    width = spec.get("width")
    if isinstance(width, bool) or not isinstance(width, int) or not 1 <= width <= 256:
        raise NodeCompileError("WIDTH_OUT_OF_RANGE")
    inputs = spec.get("inputs")
    nodes = spec.get("nodes")
    outputs = spec.get("outputs")
    if not isinstance(inputs, list) or not inputs:
        raise NodeCompileError("INPUTS_MUST_BE_NONEMPTY_LIST")
    if not isinstance(nodes, list):
        raise NodeCompileError("NODES_MUST_BE_LIST")
    if not isinstance(outputs, dict) or not outputs:
        raise NodeCompileError("OUTPUTS_MUST_BE_NONEMPTY_OBJECT")

    input_names = [_identifier(item, "input") for item in inputs]
    if len(set(input_names)) != len(input_names):
        raise NodeCompileError("DUPLICATE_INPUT")
    known = set(input_names)
    node_names: list[str] = []
    statements: list[str] = []
    declarations: list[str] = []

    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise NodeCompileError(f"NODE_MUST_BE_OBJECT:{index}")
        node_id = _identifier(node.get("id"), f"node[{index}].id")
        if node_id in known:
            raise NodeCompileError(f"DUPLICATE_NODE_ID:{node_id}")
        op = node.get("op")
        if op == "const":
            if set(node) != {"id", "op", "value"}:
                raise NodeCompileError(f"INVALID_CONST_FIELDS:{node_id}")
            value = node.get("value")
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < (1 << width):
                raise NodeCompileError(f"CONST_OUT_OF_RANGE:{node_id}")
            expression = f"{width}'d{value}"
        else:
            if not isinstance(op, str) or op not in _OPERATORS:
                raise NodeCompileError(f"UNSUPPORTED_OPERATOR:{node_id}")
            if set(node) != {"id", "op", "inputs"}:
                raise NodeCompileError(f"INVALID_NODE_FIELDS:{node_id}")
            refs = node.get("inputs")
            arity, build_expression = _OPERATORS[op]
            if not isinstance(refs, list) or len(refs) != arity:
                raise NodeCompileError(f"INVALID_ARITY:{node_id}")
            for ref in refs:
                if not isinstance(ref, str) or ref not in known:
                    raise NodeCompileError(f"UNKNOWN_OR_FORWARD_REFERENCE:{node_id}:{ref}")
            expression = build_expression(refs)
        declarations.append(f"  logic [{width - 1}:0] {node_id};")
        statements.append(f"  assign {node_id} = {expression};")
        node_names.append(node_id)
        known.add(node_id)

    output_names: list[str] = []
    for port, source in outputs.items():
        port_name = _identifier(port, "output")
        if port_name in known or port_name in output_names:
            raise NodeCompileError(f"OUTPUT_NAME_COLLISION:{port_name}")
        if not isinstance(source, str) or source not in known:
            raise NodeCompileError(f"UNKNOWN_OUTPUT_SOURCE:{port_name}")
        output_names.append(port_name)

    ports = [f"input  logic [{width - 1}:0] {name}" for name in input_names]
    ports.extend(f"output logic [{width - 1}:0] {name}" for name in output_names)
    statements.extend(f"  assign {port} = {source};" for port, source in outputs.items())
    body = declarations + statements
    lines = [
        "// Generated by brain_v12.asic.node_compiler; combinational RTL only.",
        "// Design output only: simulation, synthesis, physical hardware and fabrication are unverified.",
        f"module {module} (",
        ",\n".join(f"  {port}" for port in ports),
        ");",
        *body,
        "endmodule",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, help="JSON hardware-node graph")
    parser.add_argument("--output", required=True, help="Output SystemVerilog path")
    args = parser.parse_args()
    try:
        spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
        rtl = compile_graph(spec)
    except (OSError, json.JSONDecodeError, NodeCompileError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, sort_keys=True))
        return 2
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rtl, encoding="utf-8")
    print(json.dumps({
        "status": "DESIGN_GENERATED",
        "artifact": str(output),
        "rtl_simulation": "NOT_RUN",
        "synthesis": "NOT_RUN",
        "physical_hardware": "NOT_VERIFIED",
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
