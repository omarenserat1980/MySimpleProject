# Brain Software-Node Discovery

## Purpose

Electronic Brain needs to distinguish locally observed software capabilities
from physical devices, remote executors, simulated resources, and verified
live services. The adapter inventories runtime facts and repository source
modules without executing tools or contacting devices.

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
selected executable availability, known component presence, and a bounded
source inventory from `brain_v12/brain`, `tools`, `self_healing`, `cloud`,
and `generated_tools`. The source inventory is capped at 2,000 Python files
and excludes common cache/vendor directories. It does not read environment
variable values, API tokens, process command lines, or private keys.

To produce a conservative capability-gap report from the inventory logic:

```powershell
python -m brain_v12.brain.software_capability_gap_audit
```

To save it to a new path, use `--output` with a path that does not already exist.
The report is plan-only: it does not mutate the capability registry, launch
proposed tools, probe devices, or enable mining. Locally detected tools are
marked observed but not runtime-verified until a separate test supplies evidence.

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

The source inventory is not a dynamic runtime plugin registry. It may omit
modules outside the declared roots, non-Python tools, dynamically loaded
components, and services running in other processes or devices.

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
