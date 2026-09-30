# Brain Worker Protocol

Brain Cloud is provider-neutral. Cloudflare, GitHub Actions, a user-owned PC/phone, or another user-owned host may act as a Worker; no provider is the Brain itself.

## Worker contract

A worker must:
- register a stable worker_id and capabilities;
- emit a heartbeat at least every 60 seconds while healthy;
- claim jobs with a lease/attempt id;
- execute only capabilities it advertises;
- return evidence, status, timestamps, and artifact references;
- stop safely when its lease expires;
- never move money, publish externally, submit applications, sign contracts, or change policy without AuthorizationGate approval.

## Control-plane states

DISCOVERED -> REGISTERED -> HEALTHY -> LEASED -> RUNNING -> VERIFIED -> RELEASED

Failure paths use FAILED -> RETRYING and bounded retry policy.

## Provider adapters

- github-actions: short-lived executor; not a 24/7 host.
- cloudflare: API/queue/control-plane adapter only; heavy FFmpeg/model work stays on a Worker.
- local: user-owned PC/phone/Brain emulator executor.
- Future providers may implement the same contract without changing Brain core.

## Evidence

A green workflow is not sufficient. Production jobs require artifact existence, integrity checks, and task-specific verification. Film production additionally requires FFmpeg/ffprobe QC and VERIFIED_COMPLETED.

## Cost and safety

The core must not require Oracle, Google Cloud, Render, or paid media APIs. External services are optional adapters. Secrets stay outside the repository.
