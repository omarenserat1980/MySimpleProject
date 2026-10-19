"""Deterministic JSON graph to combinational SystemVerilog compiler.

Generated RTL is a design artifact only; it does not prove simulation,
synthesis, device programming, or physical fabrication.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
OPS = {
    "add": (2, lambda a: f"{a[0]} + {a[1]}"),
    "sub": (2, lambda a: f"{a[0]} - {a[1]}"),
    "and": (2, lambda a: f"{a[0]} & {a[1]}"),
    "or": (2, lambda a: f"{a[0]} | {a[1]}"),
    "xor": (2, lambda a: f"{a[0]} ^ {a[1]}"),
    "not": (1, lambda a: f"~{a[0]}"),
    "pass": (1, lambda a: a[0]),
}


class NodeCompileError(ValueError):
    """Raised when a graph is invalid or unsafe to compile."""


def _ident(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value) or value.startswith("__"):
        raise NodeCompileError(f"INVALID_IDENTIFIER:{label}")
    return value


def compile_graph(spec: dict[str, Any]) -> str:
    """Validate a topologically ordered graph and emit combinational RTL."""
    if not isinstance(spec, dict):
        raise NodeCompileError("SPEC_MUST_BE_OBJECT")
    unknown = set(spec) - {"module", "width", "inputs", "nodes", "outputs"}
    if unknown:
        raise NodeCompileError("UNKNOWN_SPEC_FIELDS:" + ",".join(sorted(map(str, unknown))))
    module = _ident(spec.get("module"), "module")
    width = spec.get("width")
    if isinstance(width, bool) or not isinstance(width, int) or not 1 <= width <= 256:
        raise NodeCompileError("WIDTH_OUT_OF_RANGE")
    inputs, nodes, outputs = spec.get("inputs"), spec.get("nodes"), spec.get("outputs")
    if not isinstance(inputs, list) or not inputs:
        raise NodeCompileError("INPUTS_MUST_BE_NONEMPTY_LIST")
    if not isinstance(nodes, list):
        raise NodeCompileError("NODES_MUST_BE_LIST")
    if not isinstance(outputs, dict) or not outputs:
        raise NodeCompileError("OUTPUTS_MUST_BE_NONEMPTY_OBJECT")
    input_names = [_ident(item, "input") for item in inputs]
    if len(set(input_names)) != len(input_names):
        raise NodeCompileError("DUPLICATE_INPUT")
    known = set(input_names)
    declarations, assignments = [], []
    for i, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise NodeCompileError(f"NODE_MUST_BE_OBJECT:{i}")
        name = _ident(node.get("id"), f"node[{i}].id")
        if name in known:
            raise NodeCompileError(f"DUPLICATE_NODE_ID:{name}")
        op = node.get("op")
        if op == "const":
            if set(node) != {"id", "op", "value"}:
                raise NodeCompileError(f"INVALID_CONST_FIELDS:{name}")
            value = node.get("value")
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < (1 << width):
                raise NodeCompileError(f"CONST_OUT_OF_RANGE:{name}")
            expr = f"{width}'d{value}"
        else:
            if not isinstance(op, str) or op not in OPS:
                raise NodeCompileError(f"UNSUPPORTED_OPERATOR:{name}")
            if set(node) != {"id", "op", "inputs"}:
                raise NodeCompileError(f"INVALID_NODE_FIELDS:{name}")
            refs = node.get("inputs")
            arity, build = OPS[op]
            if not isinstance(refs, list) or len(refs) != arity:
                raise NodeCompileError(f"INVALID_ARITY:{name}")
            if any(not isinstance(ref, str) or ref not in known for ref in refs):
                raise NodeCompileError(f"UNKNOWN_OR_FORWARD_REFERENCE:{name}")
            expr = build(refs)
        declarations.append(f"  logic [{width - 1}:0] {name};")
        assignments.append(f"  assign {name} = {expr};")
        known.add(name)
    output_names = []
    for port, source in outputs.items():
        port = _ident(port, "output")
        if port in known or port in output_names:
            raise NodeCompileError(f"OUTPUT_NAME_COLLISION:{port}")
        if not isinstance(source, str) or source not in known:
            raise NodeCompileError(f"UNKNOWN_OUTPUT_SOURCE:{port}")
        output_names.append(port)
    ports = [f"input  logic [{width - 1}:0] {name}" for name in input_names]
    ports.extend(f"output logic [{width - 1}:0] {name}" for name in output_names)
    assignments.extend(f"  assign {port} = {source};" for port, source in outputs.items())
    return "\n".join([
        "// Generated RTL only; simulation, synthesis and physical hardware are unverified.",
        f"module {module} (", ",\n".join(f"  {p}" for p in ports), ");",
        *declarations, *assignments, "endmodule", "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        rtl = compile_graph(json.loads(Path(args.spec).read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, NodeCompileError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, sort_keys=True))
        return 2
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(rtl, encoding="utf-8")
    print(json.dumps({"status": "DESIGN_GENERATED", "rtl_simulation": "NOT_RUN",
                      "synthesis": "NOT_RUN", "physical_hardware": "NOT_VERIFIED"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
