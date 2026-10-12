# Brain Pathway Engine

The pathway engine is a fail-closed decision layer for common Brain workflows. `BrainSupervisor.evaluate_pathway(...)` exposes it through the main supervisor and records each evaluation, next gate, and blocker list in the supervisor event trace. It
selects the first missing/unverified gate and emits stable blocker codes plus a
next action. It is evidence evaluation only: it does not run commands, deploy,
publish, restore disks, mint contracts, or change permissions.

## Supported pathways

- `code_delivery`: source snapshot → plan → tests → security review → evidence → integration.
- `windows_real_boot`: signed contract → trusted executor → actual runner probe → installed disk identity → guest boot → same-run binding → completion gate.
- `media_factory`: creative brief → assets → render integrity → cinematic QC → content review → explicit publish authorization.
- `deployment`: configuration → tests → rollback readiness → authorization → health → runtime evidence.
- `recovery`: checkpoint → integrity → rollback point → dry run → authorization → post-restore verification.

## Evidence format

Pass a JSON object keyed by gate ID. Each gate requires `verified: true`,
non-empty `evidence_id`, `source`, and `observed_at`. Specialized gates
require additional explicit fields; for example Windows guest boot requires
`os_name: "Windows Server 2025"` and `boot_source: "installed_disk"`.
The Windows pathway can also take `--expected-run-id`; the same-run binding
must match it. A READY result means all declared evidence gates were satisfied,
not that the engine itself performed the work.

## Example

```bash
PYTHONPATH=. python -m brain_v12.brain.pathway_engine \
  --pathway windows_real_boot \
  --evidence /path/to/normalized-evidence.json \
  --expected-run-id 123456
```

Exit code is 0 only for READY; 2 for BLOCKED. Output defaults to
`brain-pathway-evaluation.json`. Do not treat a locally assembled report as
authoritative unless the source evidence and signatures are independently validated.
