# Brain capability starter prototypes

This change adds a small, testable first pass across the previously proposed capabilities, while preserving the existing Brain orchestrator, resource manager, evidence store, self-healing, and mining-controller modules as the canonical production paths.

## Included prototypes
- **Auto Clicker**: PR #971 contains a disabled-by-default policy core with allowlisting, bounded clicks, postcondition verification, audit records, and emergency stop.
- **Visual Agent**: accepts a caller-supplied observation and confidence score; it does not capture a screen or claim independent device observation.
- **Task Orchestrator**: minimal state machine with a verified gate before completion; not a replacement for the existing orchestrator.
- **Resource Manager**: logical, caller-defined capacity budget; not physical CPU/RAM telemetry or OS resource reservation.
- **Evidence Engine**: in-memory hash-linked evidence records with tamper detection; not durable or independent proof.
- **Self-Healing / Recovery**: bounded retry wrapper (maximum five attempts), verifies postconditions, and stops after the limit.
- **Mining Supervisor**: fails closed unless non-simulated runtime, authenticated TLS, active worker, pool-reported share, and independent pool confirmation are all present. Revenue remains separate and requires explicit confirmation.

## Non-goals and limitations
No Android Accessibility integration, screen capture, shell execution, pool connection, share submission, credential access, financial action, or production configuration change. These prototypes do not demonstrate live mining or revenue. Use the existing production modules through reviewed adapters rather than creating parallel autonomous loops.
