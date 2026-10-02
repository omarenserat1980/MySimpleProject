# Brain Cloud UI Relaunch — v1

Date: 2026-10-02

## Decision

The project contains multiple historical interfaces. The old root `index.html` remains preserved as a legacy/reference surface. The browser-first Cloud UI is now consolidated under `cloud/web/`.

## Current classification

| Surface | Status | Role |
|---|---|---|
| `cloud/web/` | ACTIVE | Brain Cloud UI v1 |
| root `index.html` | LEGACY | Historical full control UI; not the Cloud UI source |
| `docs/` | ACTIVE/CONTENT | Film presentation and generated web assets |
| `android_executor/` | OPTIONAL | Device bridge; not required for Cloud UI |
| `cloudflare/brain-api/` | ACTIVE ADAPTER | HTTPS edge/proxy; requires configured BRAIN_ORIGIN |
| GitHub Actions | ACTIVE | Cloud execution/verification layer |

## UI v1 principles

- Browser-first; no APK or Termux required.
- Responsive on phone and desktop.
- One navigation model for Dashboard, Chat, Tasks, Agents, Media, Intelligence, Health, Audit, and Settings.
- No secrets or provider API keys in browser code.
- Fail closed when the API is missing or unavailable.
- Never display an operation as verified merely because the UI loaded.
- Preserve legacy interfaces until replacement behavior is verified.

## API contract

The UI probes the existing Cloud API surface where available:

- `GET /health`
- `GET /api/state`
- `GET /api/tasks`
- `GET /api/agents` or `GET /api/agent/status`
- `GET /api/audit` or `GET /api/events`
- `POST /api/chat`

Missing endpoints are treated as unavailable; the UI does not invent results.

## Deployment

`.github/workflows/brain-pages.yml` publishes `cloud/web` to GitHub Pages.

For a live control plane, the browser must point to a real HTTPS Brain API. The Cloudflare adapter can provide the HTTPS edge when `BRAIN_ORIGIN` is configured. GitHub Pages alone is static hosting and is not treated as the Brain backend.

## Next verification gate

1. Pages deployment succeeds.
2. Browser loads the new UI.
3. `/health` returns a real response.
4. Dashboard state is populated from the API.
5. Chat/task endpoints are tested against the actual backend.
6. Only then mark Cloud UI v1 `VERIFIED`.
