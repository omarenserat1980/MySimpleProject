# ChatGPT Suggestions & Intelligent Repair

## Runtime contract

The suggestions engine reads structured events from `BrainErrorLogStore`, calls the already-configured `OpenAIProvider`, and stores recommendations in the existing Brain SQLite database (or `BRAIN_SUGGESTIONS_DB`). It does not apply code changes or execute recommendations.

## API

All routes require `X-Brain-Control-Key`:

- `GET /api/brain/suggestions?limit=100&status=READY_FOR_REVIEW&component=fastapi&severity=ERROR&incident_id=<event_id>`
- `GET /api/brain/suggestions/{suggestion_id}`
- `POST /api/brain/suggestions/analyze` with optional JSON body `{"incident_id":"<error_event_id>","limit":10}`
- `POST /api/brain/suggestions/{suggestion_id}/approve`
- `POST /api/brain/suggestions/{suggestion_id}/reject` with `{"reason":"..."}`
- `POST /api/brain/suggestions/{suggestion_id}/verify` with `{"passed":true,"evidence":["..."]}`

An unavailable provider or invalid response creates a clearly marked local fallback suggestion with low confidence and status `NEW`. It is not represented as a ChatGPT answer. Repeated incidents are deduplicated by a stable fingerprint. Rejection requires a reason. Verification requires a positive result and non-empty evidence.

## Dashboard

Open `/brain-suggestions/` in the Brain web UI. The control key is held in the page's current memory only and is not written to local storage. Use only over a trusted connection.

## Safety and limits

Approval records a human decision; it does not execute a patch. The verification endpoint records submitted test evidence and is not a cryptographic attestation that code was deployed. A future executor must be separately authorized and must implement snapshots, allowlisted operations, tests, and rollback. Log contents are treated as untrusted evidence. Do not place secrets in error messages. Configure persistent writable storage for deployments with ephemeral filesystems.

## Verification

Run the focused tests with:

```sh
python -m pytest -q brain_v12/tests/test_error_logs.py brain_v12/tests/test_suggestions_engine.py
python -m brain_v12.self_healing.verification_gate
```

CI must pass before merging the stacked feature pull request.
