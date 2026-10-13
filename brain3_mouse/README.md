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

Mouse is still an emulator and integration foundation. It does not clone or push real repositories, merge pull requests, run GitHub Actions, deploy applications, automatically load the legacy or V12 runtime, or boot operating systems. Full runtime unification is not complete until verified in-process adapters for both actual runtimes are implemented and tested.
