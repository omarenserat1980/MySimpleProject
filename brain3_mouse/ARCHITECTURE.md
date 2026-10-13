# Brain 3 architecture boundary

```text
Legacy Brain ── simulated contract ──┐
                                     ├── Brain 3 / Mouse (local only)
Brain V12 ───── simulated contract ──┘       ├── GitHub-shaped API emulator
                                             ├── In-memory repository/issues
                                             ├── Simulated inspect/test/plan queue
                                             └── Policy gate: no execution/deploy/boot
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
