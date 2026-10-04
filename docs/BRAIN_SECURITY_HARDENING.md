# Brain Security Hardening

## Objective

Protect Brain from unauthorized access, secret leakage, abuse, accidental
destruction, and supply-chain compromise while preserving autonomous internal
operation.

## Defensive layers

1. **Fail-closed authentication** — missing control credentials never become
   anonymous access.
2. **Least privilege** — capabilities are granted per action rather than
   globally.
3. **Rate limiting** — repeated requests are bounded.
4. **Secret redaction** — operational logs/evidence must contain references and
   hashes, never credentials.
5. **Secure HTTP defaults** — security headers and no-cache defaults.
6. **CI supply-chain checks** — pinned/reviewed dependencies and secret scans.
7. **Recovery** — immutable evidence, backups, rollback and bounded repair.
8. **Detection** — repeated authentication failures and suspicious request
   patterns become security events.
9. **Financial isolation** — payment adapters remain verification/authorization
   gated.
10. **Autonomy isolation** — self-improvement cannot disable security gates.

## Required security invariant

Brain may change its own code, but it may not self-authorize a capability by
changing or deleting its own security policy. Security policy changes require
a separate protected deployment/authorization path.

## Incident response

DETECT -> CONTAIN -> PRESERVE EVIDENCE -> REVOKE/ROTATE -> PATCH -> TEST ->
VERIFY -> RESTORE

No security incident is considered resolved merely because a workflow is
green.
