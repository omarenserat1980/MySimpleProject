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

## Safety boundary

The bundle is read/compute-only. It does not:
- submit applications;
- impersonate users;
- move money;
- claim revenue without payment evidence;
- start background workers;
- create parallel self-healing loops.

## Integration rule

Mount the bundle once to avoid duplicate routes.

## Verification

The isolated bundle is covered by `test_router_bundle.py`. The main application should mount it only after the Economics test suite passes in CI.