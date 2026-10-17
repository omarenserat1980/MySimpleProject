# Brain Mining Path Audit

## Purpose

The read-only static audit helps identify duplicated mining API prefixes,
multiple simulator/adapter modules, and where known mining environment-variable
**names** are referenced. It is intended to run before consolidating routes or
changing mining configuration.

## Run

From the repository root:

```bash
python brain_v12/tools/brain_mining_path_audit.py
```

The tool emits JSON. It reports file/line locations for configuration-name
references but never reads or prints environment values. Secret files such as
`.env` and `.brain_env` are excluded. It does not access the network, start a
miner, modify files, or change production settings.

## Interpretation

- `duplicate_static_api_router_prefixes`: static duplicate declarations to
  review; not proof that both routers are registered at runtime.
- `configuration_reference_locations`: source locations for recognized
  variable names only.
- `simulator_files` and `pool_or_stratum_adapter_files`: inventory, not proof
  of active runtime use.
- `git.dirty_file_count`: count only; the audit does not print diffs.
- `real_mining_verified`, `accepted_shares_verified`, and
  `revenue_verified` remain false by design.

## Safety boundary

This tool is diagnostic only. It does not delete or migrate legacy settings.
Review findings and runtime route registration before choosing a canonical path.
