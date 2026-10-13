# Brain 3 — Mouse

Mouse is a local GitHub-shaped API emulator for Brain 3. Brain 3 now has a shared in-process kernel foundation (`unified_kernel.py`) with one memory store and one task queue for requests attributed to legacy Brain or Brain V12. This removes queue/memory separation at the Brain 3 boundary, but it does not yet mean the actual legacy and V12 runtime objects have been mounted: health reports each runtime as not integrated until a verified in-process adapter is registered.

## Non-negotiable policy

- **No real Render:** no Render SDK, service definition, deployment workflow, or Render credentials.
- **No real GitHub API calls:** Mouse's API is implemented locally and makes no outbound requests.
- **No Arkan or Redmi 3:** device setup and device execution are blocked.
- **No false Windows boot:** health, task responses, tests, and simulation cannot claim Windows Server 2025 boot success.
- **Loopback only:** default bind is `127.0.0.1:8787`; startup refuses non-loopback addresses.
- **No credentials:** never add GitHub tokens or secrets. Mouse has no authentication because it must remain local-only.
- **Memory-only state:** Mouse repositories, kernel memory, and tasks disappear when the process exits. Mouse is not a source of truth or a production replacement.
- **Unified queue:** `POST /api/brain/tasks` from either source goes into the same `brain3_shared` queue. Source is provenance only, not a separate queue.
- **Honest integration status:** `GET /api/brain3/kernel` reports shared-kernel status and separately reports whether real legacy/V12 adapters have been registered and verified. It must not report complete integration without those adapters.
- **Fail closed:** actual execution, deployment, Render, Windows boot, device setup, and publishing tasks are rejected.

## Run

From the repository root:

```bash
python -m brain3_mouse.server
```

Check health and compatibility:

```bash
curl http://127.0.0.1:8787/health
curl http://127.0.0.1:8787/api/brain/compatibility
```

Default port is `8787`. `MOUSE_PORT` can change the port, but the listener remains loopback-only.

## Brain compatibility API

- `GET /api/brain/compatibility` — describes compatibility boundaries; it is not a remote connection.
- `GET /api/brain3/kernel` — shared memory/task queue and adapter readiness status.
- `GET /api/brain3/integration` — reports initialized real in-process adapters and any import/contract errors.
- `POST /api/brain3/integrate` — explicitly attempts to initialize the actual Brain V7 and V12 runtime objects locally; integrations are marked ready only after their object-contract probes pass.
- `POST /api/brain3/tasks/{id}/dispatch` with JSON `{"adapter":"brain_v12","description":"inspect the current state"}` — dispatches a queued `inspect`, `test`, or `plan` task to a verified local adapter. This is an actual in-process safe operation, not a simulated task. It does not permit external side effects.
- `POST /api/brain/tasks` — accepts simulated `inspect`, `test`, or `plan` tasks from `legacy_brain` or `brain_v12`. Every task reports `executed: false`.
- `GET /api/brain/tasks` — lists in-memory simulated tasks.

Example request:

```bash
curl -X POST http://127.0.0.1:8787/api/brain/tasks \
  -H 'Content-Type: application/json' \
  -d '{"source":"brain_v12","action":"inspect","description":"inspect a proposed change"}'
```

Blocked actions return HTTP 403: `execute`, `deploy`, `render`, `windows_boot`, `device_setup`, and `publish`.

## Mouse GitHub-shaped API

- `GET /health`
- `GET /api/repos`
- `POST /api/repos` with JSON `{"owner":"brain3","name":"demo"}`
- `GET /api/repos/{owner}/{repo}/issues`
- `POST /api/repos/{owner}/{repo}/issues` with JSON `{"title":"example","body":"details"}`
- `GET /api/repos/{owner}/{repo}/branches`
- `GET /api/repos/{owner}/{repo}/workflows`

Unsupported mutation endpoints fail closed with HTTP 405. Unknown repositories and routes return 404.

## Tests

```bash
python -m unittest discover -s brain3_mouse/tests -v
```

Mouse remains a local-only control surface. Runtime initialization is explicit rather than automatic. The adapter bridge synchronizes runtime memory snapshots at safe operation boundaries; it does not make the two legacy storage implementations the same Python object or durable database. If a runtime import or contract probe fails, it remains unregistered and health stays false. The safe adapter surface is limited to inspect/test/plan; it does not clone or push repositories, merge pull requests, call GitHub, deploy applications, contact Render, configure devices, publish media, execute shell commands, or boot operating systems. Full unification must not be claimed unless both adapters initialize and cross-runtime memory visibility is verified.
