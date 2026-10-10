# Simulation-First Remote Fabric

## Decision

Electronic Brain uses a **simulation-first** policy for remote-device workflows. The virtual twin is the default execution substrate; ordinary physical-device/remote-control integrations are secondary and are promoted only through an explicit real-device recovery/probe step.

## Runtime contract

- `connect()` defaults to `mode=VIRTUAL`, `reality=SIMULATED`, and `policy=SIMULATION_FIRST`.
- The real probe is not called during default connection, even when configured.
- `recover_real()` is the explicit promotion path. It requires the existing real-evidence validator and Reality Gate to accept fresh real evidence.
- `prefer_real=True` is an explicit opt-in for deployments that intentionally want real-first behavior; it is not the default.
- If real evidence is missing, stale, malformed, or rejected, the gateway stays/falls back to the virtual twin.
- Simulated output is never valid proof of real hardware presence, physical connectivity, Windows Server boot, or successful real-world execution.
- The virtual endpoint is a sandbox. It must not be treated as permission to execute arbitrary commands on a real device.

## Why

The simulator is predictable, cheap, available for repeatable tests, and can exercise failure/recovery paths without waiting for a limited physical connection. Physical tools remain useful for final reality checks and operations that cannot be faithfully simulated.

## Acceptance checks

1. Default connection activates the virtual twin without invoking the real probe.
2. Simulated PowerShell commands work only through the virtual endpoint.
3. Explicit real promotion succeeds only after fresh, validated REAL evidence.
4. Invalid real evidence is rejected and the gateway falls back to simulation.
5. Reality Gate continues to reject SIMULATED evidence for REAL requirements.
