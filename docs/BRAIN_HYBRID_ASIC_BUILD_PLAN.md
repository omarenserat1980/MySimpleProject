# Brain Hybrid ASIC — Build Plan

## Purpose

This branch is a development copy of Electronic Brain V12 for planning and implementing a hybrid ASIC path. It is not a claim that a physical ASIC exists or is connected.

## Meaning of "hybrid"

Use a staged architecture:
1. **Brain software control plane** — resource registry, job scheduling, diagnostics, evidence records, and status reporting.
2. **Executable reference model** — the existing software ASIC simulator, explicitly labelled SIMULATED.
3. **Programmable-logic prototype (optional)** — FPGA or other programmable hardware for validating a hardware design before committing to a custom chip.
4. **Physical ASIC target** — a real device or hosted ASIC reached through a documented adapter and authenticated, read-only diagnostics first.
5. **Mining integration (separate gate)** — only if the target is actually a Bitcoin-mining ASIC and a pool connection is authorized and independently verified.

The word "hybrid" must not cause simulation, FPGA execution, remote-provider claims, or software emulation to be reported as a physical ASIC.

## Required proof gates

- **G0 — Software-only:** unit tests and simulator outputs are labelled as simulation.
- **G1 — Interface contract:** define a typed device adapter, capability inventory, timeouts, error handling, and a read-only diagnostic operation.
- **G2 — Identity and trust:** verify device/provider identity using a configured trust root; validate signatures cryptographically; reject caller-supplied booleans as proof.
- **G3 — Live challenge:** issue a fresh unpredictable nonce, bind it to the device identity and operation, and verify the signed response and expiry.
- **G4 — Physical evidence:** require independently verifiable device/provider evidence; a digest alone proves integrity only, not truth or physical presence.
- **G5 — Workload proof:** submit a harmless diagnostic first. Mining work is a separate explicit authorization and must produce independently verifiable pool-side evidence.
- **G6 — Economics:** report revenue only after a payout can be independently verified; simulated hashrate and dashboard balances are not revenue proof.

## Implementation rules

- Fail closed: missing verifier, trust root, device identity, fresh challenge, or signature means NOT_PROVEN.
- Never issue PHYSICALLY_ATTESTED from user-controlled evidence fields alone.
- Keep secrets out of logs, commits, evidence bundles, and chat.
- No automatic paid-resource creation, deployment, merge, wallet use, or mining-pool connection.
- Every adapter must declare whether it is SIMULATOR, FPGA, HOSTED_ASIC, or ASIC_DEVICE and expose its evidence source.
- Plugin interfaces must have versioned contracts, explicit capabilities, input validation, timeouts, and isolated tests.
- Preserve the existing ASIC simulator as a simulator; do not silently upgrade its status.

## First implementation milestones

1. Harden GEN so ordinary caller-supplied evidence cannot produce PHYSICALLY_ATTESTED.
2. Run the GEN unit tests in GitHub Actions.
3. Define a typed adapter/plugin contract and tests using fake devices only.
4. Add a read-only diagnostics interface that cannot start mining or incur charges.
5. Connect a real target only when its endpoint, identity, trust material, and authorization are available.
6. Record the resulting evidence and report each proof gate independently.

## Current verified status

The branch was created from `brain-gen-physical-proof` to preserve its GEN work. Branch creation does not build hardware. No physical ASIC connection, live challenge, mining activity, or payout is established by this document.
