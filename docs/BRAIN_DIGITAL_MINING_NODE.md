# Brain Digital Mining Node: verified-resource boundary

This change adds a read-only local preflight for a proposed Brain mining node.

## What it does
- Reports OS, architecture, logical CPU count, readable available memory, thermal-sensor availability, and presence of a miner executable.
- Checks whether required configuration variables exist without emitting their values.
- Lists blockers and evidence still required before Brain can call a worker verified.
- Never starts a miner, opens a pool connection, creates a cloud VM, or authorizes spending.

## Run on the actual device
From the repository root in Termux:

```bash
python -m brain_v12.brain.digital_mining_node
```

Exit code 0 means local preflight is ready to proceed to remote verification, not that a node is verified. Exit code 2 means blockers remain. The output is diagnostic evidence produced by the local process and is not independent attestation.

## What counts as a verified real node
The Brain control plane must authenticate a worker identity, receive a fresh authenticated heartbeat, and independently validate resource/backing evidence. Real mining additionally requires pool-derived accepted-share evidence; income requires separate payout evidence. A GitHub Actions run, simulator output, configured environment variable, or local preflight alone is not proof.

## Important constraint
This preflight does not create the physical/cloud resource. A real resource still requires an authorized host or a provider adapter with confirmed zero cost. No provider credentials, paid resource, or cloud account is assumed or created by this change.
