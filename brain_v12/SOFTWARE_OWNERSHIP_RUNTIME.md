# Brain Software Ownership & Runtime

## Objective
Give Electronic Brain a durable, evidence-backed inventory of the software, applications,
operating systems, runtimes, services, and compute substrates it is allowed to manage.
The first increment is intentionally an **inventory and evidence registry**, not an installer.

## Implemented in this increment
- SQLite-backed software records with stable IDs, category, version, source, license,
  optional install path, declared permissions, runtime state, verification state, evidence
  reference, notes, and timestamps.
- Protected API access in the Brain FastAPI application.
- Registration defaults to `planned`; only `planned`, `observed`, and `unknown` may be
  set by registration. Observed/installed/running claims require a separate evidence-bearing observation.
- A runtime observation is accepted only for an existing record and requires a non-empty
  evidence reference. A successful observation is a record of supplied evidence, not proof
  that the API independently ran a check.
- No shell execution, package installation, downloads, updates, service control, Azure
  resource creation, or deletion is performed.

## API
All endpoints require the existing Brain control key.

- `GET /api/software/status` — counts and safety boundary.
- `GET /api/software` — list records; optional `category` and `runtime_state` filters.
- `GET /api/software/{software_id}` — one record.
- `POST /api/software` — register a planned/unknown inventory item.
- `POST /api/software/{software_id}/observation` — record state and evidence reference.

Example registration body:

```json
{
  "software_id": "python-runtime",
  "name": "Python",
  "category": "runtime",
  "version": "3.x",
  "source": "system inventory",
  "license": "PSF",
  "runtime_state": "planned",
  "permissions": ["read-only"],
  "notes": "Version must be confirmed on the target executor."
}
```

## Target categories
1. Operating systems and virtual machines (Windows Server 2025 target; Linux host).
2. Runtime/toolchains (Python, .NET SDK, Git, QEMU, OVMF, FFmpeg/FFprobe).
3. Databases and state services (SQLite and approved future databases).
4. Applications and APIs (Brain V12 services and approved applications).
5. Execution substrates (GitHub runner, container/sandbox, VM executor).
6. Observability and recovery (health checks, logs, backups, restore verification).

These are inventory categories and goals, not a claim that each component is installed.

## Required next gates before execution features
- Read-only host discovery with explicit allowlist and bounded output.
- Software source and license validation; pinned versions and hashes.
- Signed/traceable task requests, least-privilege identities, per-task sandbox,
  timeouts, resource limits, network egress policy, and secret redaction.
- Plan/diff first; explicit approval for installs, upgrades, removals, system services,
  cloud resource changes, or spend.
- Backup and tested rollback before mutation; SBOM and audit trail for every change.
- Independent post-action checks and retained evidence. Action success must not be
  confused with objective success.
- Production rollout only after CI tests, security review, and an approved pull request.

## Security and semantics
- A software registry entry is not ownership of a software copyright or license.
- `verified` means the caller supplied an evidence reference for the stated observation;
  it does not mean the reference was independently validated by this module.
- No automatic software installation is enabled by this increment.
