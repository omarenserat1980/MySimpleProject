# Brain ASIC Logic Simulator v0.1

## Scope
This first in-Brain simulator is a deterministic, inspectable, software-only
two-state digital netlist simulator. It supports INPUT/CONST, basic Boolean
gates, MUX, and synchronous DFF nodes. Each cycle reports all resolved signal
values, output values, DFF next state, toggling signals, cumulative toggles,
elapsed simulated time, and explicitly labeled optional energy estimates.

## API
- `GET /api/asic-sim/status`: reports supported operations and limitations.
- `POST /api/asic-sim/run`: accepts `{"netlist":{"nodes":[...]}, "vectors":[...]}`.
  Each node has a unique `name`, an `op`, and optional named `inputs`.
  INPUT nodes must match every key in each input vector. Outputs may be listed
  in `netlist.outputs`; otherwise the final declared node is output.
- Netlist options: `clock_hz` (default 1 MHz) and
  `energy_per_toggle_pj` (default 0; user-supplied estimate only).
- Limits: 512 nodes and 10,000 cycles per run.

## Example
```json
{
  "netlist": {
    "nodes": [
      {"name":"a","op":"INPUT"},
      {"name":"b","op":"INPUT"},
      {"name":"y","op":"XOR","inputs":["a","b"]}
    ],
    "outputs":["y"],
    "clock_hz":1000000
  },
  "vectors":[{"a":0,"b":0},{"a":0,"b":1},{"a":1,"b":1}]
}
```

## Transparency and limitations
This version is not a transistor-level simulator, SPICE engine, SystemVerilog
RTL simulator, physical-design tool, thermal solver, or real ASIC measurement.
It does not model X/Z, propagation delay, metastability, setup/hold, routing,
manufacturing variation, or analog behavior. Dynamic-energy and power values
are estimates based on a caller-supplied energy-per-toggle assumption. DFFs
sample input at the end of each simulated cycle. No network, physical device,
mining pool, wallet, or external resource is contacted.

Future levels should be added as separate validated models (RTL integration,
SPICE integration, timing, layout, thermal, power-delivery and fault models),
with coverage and evidence for each rather than claiming full fidelity early.
