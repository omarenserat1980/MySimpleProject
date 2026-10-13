# Brain 3 — Mouse

Mouse is a **local GitHub-shaped API emulator** for Brain 3. It is a sandbox for testing orchestration and repository workflows without using a real GitHub API, a real GitHub repository as a runtime dependency, or Render.

## Safety and scope

- **No Render:** no Render SDK, service definition, deployment workflow, or Render credentials.
- **No real GitHub calls:** endpoints are implemented locally; the emulator never makes outbound requests.
- **Loopback only:** default bind is `127.0.0.1:8787`; startup refuses non-loopback addresses.
- **No credentials:** do not add GitHub tokens or secrets. Mouse has no authentication because it must remain local-only.
- **Memory-only state:** repositories and issues disappear when the process exits. It is not a source of truth or a production GitHub replacement.
- **Explicitly simulated:** all resources are marked `emulated: true`; health reports `real_github: false` and `render: false`.

## Run

From the repository root:

```bash
python -m brain3_mouse.server
```

Then check:

```bash
curl http://127.0.0.1:8787/health
```

Default port: `8787`. Override with `MOUSE_PORT`. The host remains loopback-only.

## Supported routes

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

This is an initial emulator, not a complete implementation of the GitHub REST API. It does not clone, push, merge, run Actions, deploy applications, or boot operating systems.
