# Economics Router Integration

The Economics subsystem exposes one isolated bundle:

```python
from .economics.router_bundle import router as economics_router
app.include_router(economics_router)
```

## Included routes

- `POST /api/economics/score`
- `POST /api/economics/revenue/verify`
- `POST /api/economics/orchestrator/evaluate`
- `POST /api/economics/shortlist`

## Economic execution chain

```
source
  -> source_identity
  -> freshness gate
  -> eligibility verification
  -> source/id deduplication
  -> deterministic score
  -> evidence-backed memory
  -> economic decision
  -> audit event
  -> application boundary (future, explicit)
  -> payment evidence
  -> confirmed revenue
```

The application boundary remains intentionally outside this package.

## Safety boundary

The bundle is read/compute-only. It does not:
- submit applications;
- impersonate users;
- move money;
- claim revenue without payment evidence;
- start background workers;
- create parallel self-healing loops.

## Verification

The isolated Economics suite includes unit tests for:
- opportunity scoring and lifecycle;
- revenue evidence;
- source verification;
- economic memory and decisioning;
- deterministic audit IDs;
- source identity and deduplication;
- freshness/expiry;
- shortlist API.

The main application should mount the bundle only after the Economics suite passes in CI.

## Current integration state

The bundle is implemented and isolated. It is **not yet mounted into `brain_v12/app.py`** because that file has a large existing route surface and must be updated from its exact current blob rather than replaced approximately.
