# Brain 3 architecture boundary

```text
Legacy Brain request ─┐
                       ├── one Brain 3 Unified Kernel (shared memory + queue)
Brain V12 request ─────┘             │
                                     ├── Mouse GitHub-shaped local emulator
                                     ├── shared inspect/test/plan task queue
                                     └── fail-closed policy gate
```

The default compatibility endpoints only queue work. A separate explicit local integration endpoint can instantiate the actual Brain V7 and V12 in-process runtime objects and register safe inspect/test/plan adapters after object and handler probes pass. Initialization is not automatic; failed imports or failed probes leave that runtime unregistered and health false.

Mouse is not a real GitHub client and never proxies to GitHub. It has no Render adapter. The listener is loopback-only, and all state is in memory. Its health response is emulator status only.

Policy gates:
- The runtime bridge exposes only inspect/test/plan operations; the wider legacy cycle and all V12 external integrations remain outside the bridge.
- Runtime-specific memory snapshots are synchronized through the Brain 3 shared ledger at adapter boundaries; this does not merge the runtimes' storage internals into one Python object or durable database.
- Queueing remains non-executing by default. A task runs only after explicit dispatch to a verified local adapter.
- Render and all external network calls are disabled.
- Arkan and Redmi 3 setup are prohibited.
- Windows Server 2025 boot proof must come from the real guest and independent completion gates; Mouse cannot produce or imply that proof.
- A future real provider would require a separate explicitly authorized adapter; it must not silently replace Mouse or call Render.


## Integration truth

The shared kernel is implemented and both source types enter the same queue. Actual runtime adapters are now available through explicit initialization, and the integration endpoint reports which adapters passed their in-process probes. Integration is complete only if both flags are true and a cross-runtime memory-visibility test passes. The bridge is boundary synchronization, not shared object identity; do not overstate it as a single underlying database.
