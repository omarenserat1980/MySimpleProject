# Brain Cloudflare Runtime Policy

## Decision: emulator-first, real Cloudflare as a narrow adapter

Effective default: **EMULATOR**. Brain must remain usable and testable without Cloudflare account availability, billing setup, API credentials, or R2 activation.

### Runtime modes

- `emulator` (default): use local Wrangler development and local/test fixtures. Never deploy or mutate a real Cloudflare account.
- `real-readonly`: optional, explicit, short diagnostic access to real account metadata only. Do not create/delete resources, deploy Workers, migrate remote D1, or write R2 objects.
- `real-deploy`: exceptional, explicit opt-in only. Requires `BRAIN_CLOUDFLARE_REAL=1`, configured credentials, and a deliberate operator action. This mode is not used by ordinary tests or default workflows.

### Required rules

1. No secret is needed to run emulator tests.
2. All default CI gates must use emulator/static tests and must not depend on live Cloudflare, D1, or R2 availability.
3. Real-account checks are a separate, optional workflow/job and cannot block local development or emulator tests.
4. Real Cloudflare must not be described as healthy unless a live request succeeds; configuration presence alone is not proof of connectivity.
5. Do not silently fall back from real to emulator for a production write. Mode must be visible in logs and evidence.
6. Use disposable local data for D1 and test media for R2 emulation; never mix local fixtures with live customer data.
7. Keep remote deployment and remote migrations behind explicit opt-in. Payment callbacks and revenue state must be tested with fixtures; do not trigger real payments during emulator tests.

## Local commands

From the repository root:

```bash
# Default: local emulator mode; no Cloudflare secrets required
bash cloudflare/brain-api/scripts/brain-cloudflare-mode.sh status
bash cloudflare/brain-api/scripts/brain-cloudflare-mode.sh test
bash cloudflare/brain-api/scripts/brain-cloudflare-mode.sh dev
```

`dev` starts Wrangler's local Worker development server. The local D1/R2 bindings and behavior depend on Wrangler's local support and project configuration; the emulator does not reproduce every Cloudflare production behavior.

## Narrow real-cloud boundary

Real Cloudflare is reserved for:
- occasional read-only account/health checks;
- a deliberate deployment after emulator gates pass;
- an explicitly approved remote migration or resource operation;
- a final smoke test with non-sensitive test data.

R2 activation is an account-level prerequisite and cannot be repaired by changing application code or rerunning CI. If R2 is not enabled, emulator tests must still pass and the live deploy should be reported as `BLOCKED_REAL_R2_NOT_ENABLED`, not as an emulator failure.

## Acceptance criteria

- Default mode reports `BRAIN_CLOUDFLARE_MODE=emulator`.
- Test command runs local/static tests without Cloudflare credentials.
- Deploy command refuses to run unless explicit real-deploy opt-in is supplied.
- Logs identify the selected mode and never print credentials.
