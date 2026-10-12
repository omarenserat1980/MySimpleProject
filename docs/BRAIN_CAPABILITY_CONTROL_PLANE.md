# Brain Capability Control Plane

Brain treats Android Executor, Termux Agent, Desktop Agent, and GitHub CI as workers behind one capability layer.

## Rules
- Select workers by capability, not by hard-coded device identity.
- Record evidence for successful and failed actions.
- Prefer the strongest previously verified path.
- Keep one active orchestration path per goal.
- Never bypass OS permissions or security boundaries.
- When a capability is unavailable, classify the blocker and choose an authorized fallback.

## Workers

- Android Executor: device/media/files/task execution within its allowlist.
- Termux Agent: Python/FFmpeg/filesystem capabilities granted by Termux.
- Desktop Agent: filesystem/process/build capabilities granted by the desktop bridge.
- GitHub Actions: build/test/artifact/verification capabilities.

## Independence model

ChatGPT is a planning and knowledge partner. It is not required for every individual tool operation once Brain has an authorized worker and a verified path.

Flow:

Problem -> capability discovery -> best path -> authorized execution -> evidence -> verification -> path evolution.
