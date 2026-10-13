# Preliminary physical prototype plan

## Gate 0 — Requirements

Define target function, I/O voltage standards, clock target, expected throughput,
memory needs, interfaces, safety constraints, budget, and acceptance tests. No
board or silicon is presumed to exist.

## Gate 1 — RTL validation

Run lint and RTL simulation using an installed, identified tool. Retain exact
commands, tool version, exit status, test vectors, and output artifacts. If no
tool is installed, report the missing dependency and stop this gate without
claiming a pass.

## Gate 2 — Synthesis and implementation estimate

Use a documented synthesis flow (for example, Yosys if already available) to
generate a netlist. Physical area/timing/power estimates must name the target
technology, constraints, tool version, and assumptions. Generic estimates are
not measured silicon characteristics.

## Gate 3 — FPGA prototype

Only after requirements and budget review, select a compatible FPGA board and
verify voltage, clock, programming interface, power, and thermal requirements
from its official datasheet. No purchase or provisioning is authorized by this
plan.

## Gate 4 — Physical ASIC consideration

Custom silicon requires technology/library selection, design-rule constraints,
timing constraints, synthesis, place-and-route, DRC/LVS where applicable, signoff,
foundry submission, packaging, and physical bring-up. These steps must not be
represented as complete unless evidence exists.

## Evidence record

For each stage retain: stage ID, source revision, tool and version, exact command,
start/end time, exit status, artifact references and hashes, reviewer, result,
and unresolved blockers. Do not place secrets in evidence logs.
