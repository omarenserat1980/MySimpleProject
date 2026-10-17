# Brain SHA-256d execution and evidence contract

Contract version: `brain.sha256d.execution.v1`

This contract separates three different claims. A successful result in one layer never upgrades evidence for another layer.

## Execution layers

| `execution_mode` | `execution_layer` | Required proof | Permitted status |
|---|---|---|---|
| `SIMULATOR` | `PYTHON_SOFTWARE` | Bounded software hashing, result object, and Brain evidence hash verification | `SIMULATION_ONLY` or `SOFTWARE_VERIFIED` in the UI after known-answer checks |
| `RTL_SIMULATION` | RTL toolchain (Icarus Verilog + VVP) | Successful compilation, successful simulator exit, expected pass marker, expected Genesis nonce and attempt count, and Brain evidence hash verification | `RTL_SIMULATION_VERIFIED` |
| physical device | External device | Attested device identity, fresh authenticated heartbeat, and result received from that device | Not available in the software-only workflow |
| pool/share/revenue | External mining service | Independently verifiable pool job/share acceptance and separate payout/revenue evidence | Not asserted by either local test |

## Interfaces

- `POST /api/asic-sim/sha256d-pow`: bounded Python software proof-of-work simulation.
- `POST /api/asic-sim/sha256d-rtl-self-test`: compiles and executes the repository RTL known-answer testbench. It does not fall back to Python.
- MCP tool `brain.asic_sha256d_simulate`: software-only simulation.
- MCP tool `brain.asic_sha256d_rtl_self_test`: actual RTL testbench execution, when Icarus Verilog and VVP are installed.

## Fail-closed requirements

- Missing toolchain or source files must return a blocked status.
- Compilation failure, simulator failure, timeout, missing pass marker, wrong nonce, or wrong attempt count must never be marked verified.
- A task may be completed only after successful execution and verification of the evidence-store record.
- `rtl_executed`, `physical_asic_executed`, `pool_acceptance_verified`, and `revenue_verified` are independent booleans. They must not be inferred from one another.
- A host CPU benchmark is not a measurement of RTL performance, ASIC performance, pool acceptance, or revenue.

## Operational boundary

The API and MCP operations are local bounded tests. They do not start a physical miner, connect to a pool, submit shares, handle wallet funds, deploy production services, or change production secrets. The Arabic Brain simulator UI may display a layer as verified only after the corresponding live API response and evidence fields meet that layer's criteria.
