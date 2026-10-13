# Brain 3 — Mouse

Mouse is a local GitHub-shaped API emulator and compatibility boundary for Brain 3. It can accept simulated requests from the legacy Brain and Brain V12 without contacting either runtime, GitHub, Render, or a device.

## Non-negotiable policy

- **No real Render:** no Render SDK, service definition, deployment workflow, or Render credentials.
- **No real GitHub API calls:** Mouse's API is implemented locally and makes no outbound requests.
- **No Arkan or Redmi 3:** device setup and device execution are blocked.
- **No false Windows boot:** health, task responses, tests, and simulation cannot claim Windows Server 2025 boot success.
- **Loopback only:** default bind is `127.0.0.1:8787`; startup refuses non-loopback addresses.
- **No credentials:** never add GitHub tokens or secrets. Mouse has no authentication because it must remain local-only.
- **Memory-only state:** repositories and tasks disappear when the process exits. Mouse is not a source of truth or a production replacement.
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

- `GET /api/brain/compatibility` — describes the legacy Brain and V12 compatibility contract. This is metadata, not a remote connection.
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

Mouse is an initial emulator. It does not clone or push real repositories, merge pull requests, run GitHub Actions, deploy applications, invoke old/new Brain processes, or boot operating systems.
