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
