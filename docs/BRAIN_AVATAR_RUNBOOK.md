# Brain Avatar — Runtime and Verification Runbook

## Current implementation

The avatar page is stored at `brain_v12/web/brain-avatar/index.html`. The FastAPI application mounts `brain_v12/web` at `/` with HTML index resolution, so the expected page route is:

- UI: `/brain-avatar/`
- State endpoint: `/api/brain-avatar/state`

The state endpoint may persist a rate-limited `HUMAN_PRESENCE` pulse through the canonical memory store. It is not strictly read-only and does not trigger device execution.

## Run locally (zero-cost)

From the repository root, start the existing FastAPI app using the project's installed dependencies:

```bash
python -m uvicorn brain_v12.app:app --host 127.0.0.1 --port 8012
```

Then open these URLs in a browser on the same device:

- `http://127.0.0.1:8012/brain-avatar/`
- `http://127.0.0.1:8012/api/brain-avatar/state`

If the app is already running on port 8012, do not start a second instance. If the command fails due to missing dependencies or configuration, record the exact error and follow the repository's existing bootstrap instructions rather than installing paid services.

## Verification checklist

1. Confirm the HTML page returns successfully and shows the Arabic RTL avatar interface.
2. Confirm the state endpoint returns JSON and a recognized avatar state.
3. Confirm the page's state polling updates the UI without a JavaScript error.
4. Check the page at a narrow mobile viewport and with reduced-motion preferences.
5. Run `python -m pytest -q brain_v12/tests/test_brain_avatar_contract.py` in an authorized environment.
6. Record the exact commit SHA and CI run URLs for test evidence.

## Evidence boundaries

- A passing contract test proves the tested code contract, not that a real phone rendered the page.
- A successful API response proves the endpoint responded, not that the face was visibly rendered.
- UI polling can create a bounded pulse tick; it does not prove an independent always-on background heartbeat.
- This page is served by the Brain application. Do not assume a public hosted URL or GitHub Pages deployment unless a separate deployment is configured and verified.
- No camera, facial recognition, cross-app overlay, paid resource, or physical-device access is required for the local smoke test.

## Current known gaps

- Real browser/device rendering still requires an observed smoke test.
- A continuously running background heartbeat has not been independently demonstrated.
- Keep the implementation on `feature/human-like-cognition` until the project owner explicitly approves merging.
