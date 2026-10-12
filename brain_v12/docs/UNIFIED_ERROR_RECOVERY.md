# Brain Unified Error Recovery

## Purpose

Unify error reports from Termux Brain, Desktop Commander Brain, Azure Brain,
GitHub Brain, and the Brain runtime. The intake normalizes source and context,
redacts likely secrets, fingerprints duplicate incidents, stores JSONL evidence,
and optionally forwards the safe report to the Brain Chat Simulator.

## API

All endpoints use the existing Brain control-key authentication contract.

- `POST /api/errors/report`: JSON body with `source`, `message` (or `error`),
  optional `severity`, and optional `context`.
- `GET /api/errors/recent?limit=50`: return recent reports (limit 1–200).

Allowed source values: `termux-brain`, `desktop-commander-brain`,
`azure-brain`, `github-brain`, `brain-runtime`.

## Chat Simulator forwarding

Set `BRAIN_CHAT_SIMULATOR_URL` to an authenticated, trusted endpoint that accepts
the JSON webhook envelope. If unset, reports are stored and the response clearly
says `NOT_CONFIGURED`; this is not represented as a successful ChatGPT handoff.
Do not point this variable at an untrusted public URL. The simulator should return
diagnosis, root-cause hypotheses, proposed scripts/tools, tests, and rollback steps.

## Storage and safety

Default store: `.brain/state/error-recovery.jsonl`; override with
`BRAIN_ERROR_STORE`. Likely secrets are redacted before persistence/forwarding.
This is defense-in-depth, not a guarantee that every secret format is recognized.
Reports never trigger code execution. Proposed changes must pass existing Brain
permissions, isolated tests, verification, and evidence gates before deployment.

## Node reporting examples

Termux, GitHub Actions, Azure, and Desktop Commander integrations should send the
same JSON contract to the Brain API with their source value and a concise error
message plus redacted context. Keep control keys in environment/secret stores;
never place credentials in the request body.
