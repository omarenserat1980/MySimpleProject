# Brain Capability Fabric

Brain is not bound to a limited set of applications. Tasks declare a capability and Brain selects an available executor.

Intent -> Plan -> Capability -> Executor -> Verify -> Evidence -> Learn

Rules:
- Multiple executors may provide one capability.
- Executors are ranked deterministically.
- Failed executors use bounded fallbacks.
- Permissions are filtered before execution.
- No executor means FAILED, never synthetic success.
- Provider identity is an implementation detail, not the task contract.
- Verification and evidence remain required for objective completion.
- ChatGPT is one AI partner, not a single point of failure.

Initial capability families: code, media.render, media.image, media.audio, search, browser, document, data.analysis, ai.reasoning, ai.generation, device, compute, storage, automation, publish.

CI status: this contract is guarded by the dedicated Brain Capability Fabric workflow.


## Autonomy and continuity policy

Brain uses a three-tier execution order:

1. **BRAIN_OWNED** — Brain's own maintained code, applications, local engines, agents, and repair mechanisms are preferred first.
2. **FREE_DIVERSE** — independent free/open-source or otherwise no-cost executors are used next, with multiple independent alternatives preferred over a single provider.
3. **PAID_EXTERNAL** — paid providers are a last resort only when commercial funding is explicitly enabled and the required permission exists.

This ordering is enforced before health-based ranking inside each tier. A healthy paid provider cannot outrank an eligible Brain-owned executor merely because it is faster or more available.

Brain must continuously favor:
- self-diagnosis -> self-repair -> self-test -> self-upgrade;
- preservation of working versions and rollback evidence before self-modification;
- provider diversity and bounded fallback to avoid single-source dependency;
- objective verification after every consequential execution;
- explicit authorization for external side effects, publishing, purchases, contracts, or financial commitments.

Paid capability is therefore an optional economic layer, not a dependency of Brain's core survival or development.
