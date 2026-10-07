# Brain V13 Evidence / Verification Core

The Brain control plane distinguishes CI evidence from runtime evidence.

Lifecycle:
MISSION → EXECUTE → OBSERVE → EVIDENCE → VERIFY → COMPLETE

Rules:
- CI success cannot by itself prove runtime success.
- Runtime evidence is append-only and hash-checked.
- A requested evidence kind must exist before a success claim is accepted.
- Verification is policy/state logic; the single BrainSupervisor remains the authoritative orchestrator.
- Evidence verification does not create retries or control loops.

The supervisor records observations into EvidenceStore and exposes verify_evidence() for the completion path. BrainConstitution remains the final policy gate for success claims.
