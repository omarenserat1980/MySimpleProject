# Brain Software-Node Discovery

## Purpose

Electronic Brain needs to distinguish the software capabilities it can observe
locally from physical devices, remote executors, simulated resources, and
verified live services. This first discovery adapter inventories local runtime
facts and repository components without executing tools or contacting devices.

## Run on the Windows computer

From the repository root in PowerShell:

```powershell
python -m brain_v12.brain.software_node_discovery
```

To save an evidence report at a new path (existing files are never overwritten):

```powershell
python -m brain_v12.brain.software_node_discovery --output .brain\state\software_node_inventory.json
```

The report includes OS/Python facts, optional Python module availability,
selected executable availability, and the presence of known Brain component
files. It does not read environment-variable values, API tokens, process
command lines, or private keys.

## Evidence levels

- `PRESENT`: a module, executable, or source file was found.
- `NOT_FOUND`: it was not found in this local inspection.
- `HEALTHY`: **not** inferred by this tool; requires a separate bounded health
  check with its own evidence.
- `REMOTE_REACHABLE`: **not** inferred; requires an explicitly authorized
  network/device probe.
- `PHYSICAL_MINER_ACTIVE`: **not** inferred; requires worker telemetry and
  independent live evidence from the real device/pool.
- `REVENUE_REALIZED`: **not** inferred; requires verified payout evidence.

## Safe self-improvement loop

1. Discover inventory and write evidence.
2. Compare capabilities against task requirements and report missing nodes.
3. Propose the smallest change; do not edit source during discovery.
4. Create a candidate on an isolated branch.
5. Run focused tests, static checks, and applicable smoke tests.
6. Preserve logs, hashes, and baseline commit in evidence.
7. Require human review for permission, network, device, financial, publishing,
   destructive, or production changes.
8. Accept only after verification; otherwise reject/rollback the candidate.

This module is a first inventory adapter, not a claim that the whole Brain
self-evolution loop is wired to it. A later integration must connect it to the
capability registry and supervisor through tests and explicit permissions.
