# Brain Continuous Self-Improvement Architecture

Required loop:

RUN -> OBSERVE -> DIAGNOSE -> GENERATE CANDIDATE -> VALIDATE PATCH -> APPLY -> TEST -> VERIFY -> RETRY

Rules:
- A repair command succeeding is not success.
- A candidate must pass patch validation before application.
- Only configured repair roots may be changed.
- Security and workflow files are outside the default repair roots.
- Secrets are redacted from persisted environment diagnostics.
- Attempts and verification results are persisted.
- Attempts and command timeouts are bounded.
- One supervisor lock prevents concurrent self-modification.
- Persistent commits are a separate explicit gate.

Generator interface:
Set BRAIN_CODE_GENERATOR_COMMAND to a Brain code-generation provider.
The provider receives BRAIN_REPAIR_FAILURE_FILE and must print only a unified git diff.
code_repair_agent.py validates and applies that diff.

The generator can later be a local model, an internal Brain agent, or another
approved provider without changing the supervisor.

The current GitHub workflow verifies changes in an ephemeral runner. Automatic
commits are intentionally disabled by default; persistence should happen only
after verification and a rollback point are established.
