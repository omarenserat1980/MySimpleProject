# Brain 3 architecture boundary

```text
Legacy Brain request ─┐
                       ├── one Brain 3 Unified Kernel (shared memory + queue)
Brain V12 request ─────┘             │
                                     ├── Mouse GitHub-shaped local emulator
                                     ├── shared inspect/test/plan task queue
                                     └── fail-closed policy gate
```

The compatibility endpoints describe and accept simulated requests from both legacy Brain and Brain V12. They do not connect to, launch, or modify either runtime. This keeps the third Brain isolated while allowing contract tests for both sides.

Mouse is not a real GitHub client and never proxies to GitHub. It has no Render adapter. The listener is loopback-only, and all state is in memory. Its health response is emulator status only.

Policy gates:
- Legacy Brain is compatibility-only; old execution paths remain disabled.
- Brain V12 can submit simulated inspect/test/plan tasks only; no remote execution.
- Render and all external network calls are disabled.
- Arkan and Redmi 3 setup are prohibited.
- Windows Server 2025 boot proof must come from the real guest and independent completion gates; Mouse cannot produce or imply that proof.
- A future real provider would require a separate explicitly authorized adapter; it must not silently replace Mouse or call Render.


## Integration truth

The shared kernel is implemented and the Mouse HTTP task endpoint now submits both source types to the same queue. This is real unification of Brain 3's coordination boundary, not yet full consolidation of the legacy and V12 runtime implementations. No verified in-process adapters for those actual runtime objects are registered by default. `/api/brain3/kernel` must report both integration flags as false until each runtime adapter is implemented and verified. Do not describe the whole Brain as fully unified until that gate passes.
